"""Geometry helpers for the schematic (non-AI) face drawing.

Everything is expressed in a 1000 x 1000 "design space" with the face centred on x = 500.
The renderer scales design units to pixels, so the drawing code never mentions pixels.
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass, field

CX = 500.0  # horizontal centre line of the face

Point = tuple[float, float]

# Half-width of the face (distance from the centre line) at several heights.
# Each list is (y, half_width) from the top of the skull down to the chin point (half_width = 0).
FACE_PROFILES: dict[str, list[Point]] = {
    "oval": [(150, 0), (165, 112), (230, 190), (330, 231), (450, 238), (560, 222), (650, 186), (725, 126), (775, 62), (793, 0)],
    "round": [(188, 0), (198, 122), (258, 214), (350, 256), (450, 268), (560, 262), (650, 236), (730, 178), (786, 96), (806, 0)],
    "square": [(160, 0), (172, 116), (235, 196), (330, 233), (450, 246), (560, 244), (650, 236), (735, 222), (778, 172), (796, 92), (801, 0)],
    "long": [(112, 0), (127, 100), (195, 172), (300, 205), (450, 216), (580, 206), (700, 174), (800, 124), (852, 60), (872, 0)],
    "heart": [(150, 0), (165, 126), (225, 216), (320, 256), (430, 262), (540, 226), (640, 166), (720, 100), (775, 46), (795, 0)],
    "triangular": [(162, 0), (174, 96), (236, 152), (330, 186), (450, 216), (560, 236), (660, 246), (740, 216), (786, 146), (806, 70), (813, 0)],
}
NEUTRAL_SHAPE = "oval"


def catmull_rom(points: list[Point], per_segment: int = 10, start_ghost: Point | None = None, end_ghost: Point | None = None) -> list[Point]:
    """A smooth curve through ``points``. Optional 'ghost' neighbours control the end tangents."""
    if len(points) < 3:
        return list(points)
    ext = [start_ghost or points[0], *points, end_ghost or points[-1]]
    out: list[Point] = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for j in range(per_segment):
            t = j / per_segment
            t2, t3 = t * t, t * t * t
            out.append(
                (
                    0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                    0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3),
                )
            )
    out.append(points[-1])
    return out


def mirror_x(points: list[Point]) -> list[Point]:
    return [(2 * CX - x, y) for x, y in points]


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def offset_curve(points: list[Point], distances: list[float]) -> list[Point]:
    """Move each point of a curve sideways (to the outside of the right half-face) by ``distances``."""
    out: list[Point] = []
    n = len(points)
    for i, (x, y) in enumerate(points):
        x0, y0 = points[max(0, i - 1)]
        x1, y1 = points[min(n - 1, i + 1)]
        tx, ty = x1 - x0, y1 - y0
        length = math.hypot(tx, ty) or 1.0
        nx, ny = ty / length, -tx / length  # right-hand normal; points away from the face on the right half
        if nx < 0 or (abs(nx) < 1e-9 and ny > 0):  # keep the normal pointing outward / upward
            nx, ny = -nx, -ny
        d = distances[i]
        out.append((x + nx * d, y + ny * d))
    return out


@dataclass
class Face:
    """The resolved face: contour plus the vertical positions of every feature."""

    shape: str
    right: list[Point]  # dense right-half contour, top -> chin
    top: float = 0.0
    chin: float = 0.0
    height: float = 0.0
    eye_y: float = 0.0
    brow_y: float = 0.0
    nose_y: float = 0.0  # base of the nose
    mouth_y: float = 0.0
    hairline_y: float = 0.0
    _ys: list[float] = field(default_factory=list, repr=False)
    _hw: list[float] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self.top = self.right[0][1]
        self.chin = self.right[-1][1]
        self.height = self.chin - self.top
        self._ys = [p[1] for p in self.right]
        self._hw = [p[0] - CX for p in self.right]
        self.eye_y = self.top + 0.50 * self.height
        self.brow_y = self.eye_y - 0.075 * self.height
        self.nose_y = self.top + 0.705 * self.height
        self.mouth_y = self.top + 0.815 * self.height
        self.hairline_y = self.top + 0.19 * self.height

    def hw(self, y: float) -> float:
        """Half-width of the face at height ``y`` (linear interpolation along the contour)."""
        if y <= self._ys[0]:
            return self._hw[0]
        if y >= self._ys[-1]:
            return self._hw[-1]
        i = bisect.bisect_right(self._ys, y)
        y0, y1 = self._ys[i - 1], self._ys[i]
        t = 0.0 if y1 == y0 else (y - y0) / (y1 - y0)
        return lerp(self._hw[i - 1], self._hw[i], t)

    @property
    def eye_dx(self) -> float:
        return 0.40 * self.hw(self.eye_y)

    @property
    def eye_w(self) -> float:
        return 0.40 * self.hw(self.eye_y)

    def right_between(self, y_from: float, y_to: float) -> list[Point]:
        return [p for p in self.right if y_from <= p[1] <= y_to]

    def outline(self) -> list[Point]:
        """Closed contour: right half down to the chin, left half back up."""
        return self.right + mirror_x(self.right)[::-1]


def build_face(shape: str | None, *, jaw_scale: float = 1.0) -> Face:
    profile = FACE_PROFILES.get(shape or NEUTRAL_SHAPE, FACE_PROFILES[NEUTRAL_SHAPE])
    # jaw_scale narrows or widens the lower half of the face a little (used for apparent gender)
    top_y, chin_y = profile[0][0], profile[-1][0]
    control: list[Point] = []
    for y, hw in profile:
        t = (y - top_y) / (chin_y - top_y)
        scale = 1.0 + (jaw_scale - 1.0) * max(0.0, (t - 0.45) / 0.55)
        control.append((CX + hw * scale, y))
    ghost_start = (CX - (control[1][0] - CX), control[1][1])
    ghost_end = (CX - (control[-2][0] - CX), control[-2][1])
    dense = catmull_rom(control, per_segment=14, start_ghost=ghost_start, end_ghost=ghost_end)
    return Face(shape=shape or NEUTRAL_SHAPE, right=dense)
