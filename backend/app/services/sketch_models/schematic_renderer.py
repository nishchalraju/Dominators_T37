"""Rule-based schematic face drawing (NOT artificial intelligence).

Every attribute from the controlled vocabulary changes real geometry: face contour, hair,
eyebrows, eyes, nose, mouth, facial hair, glasses and age lines. The drawing is
deterministic - the same attributes always give byte-identical PNG files - and it is
a *generic composite diagram*, not a likeness of any person.

Unspecified attributes are drawn in a neutral form and reported in ``unspecified``.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import random
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

from app.services.attributes import ATTRIBUTE_BY_KEY, ATTRIBUTE_KEYS, Attributes
from app.services.sketch_models.schematic_geometry import (
    CX,
    Face,
    Point,
    build_face,
    catmull_rom,
    mirror_x,
    offset_curve,
)

SIZE = 1024  # output size in pixels
SS = 2  # supersampling factor (draw at 2x, shrink for smooth edges)
K = SIZE * SS / 1000.0  # design units -> pixels at the drawing resolution
RENDERER_VERSION = "1.1"  # 1.1: skin colour (white / brown / black) is drawn; 1.0 had no colour

# palette (grey / sepia "pencil on paper")
PAPER = (244, 241, 233)
INK = (36, 38, 44)
INK_SOFT = (88, 91, 100)
HAIR = (66, 69, 78)
HAIR_DARK = (30, 32, 38)
HAIR_LIGHT = (104, 107, 117)
EYE_WHITE = (250, 249, 246)
GARMENT = (214, 211, 203)
LENS = (196, 208, 218)

RGB = tuple[int, int, int]


@dataclass(frozen=True)
class SkinPalette:
    """Every colour that depends on the skin colour, so one choice changes the whole face consistently."""

    skin: RGB  # face, neck and ears
    shade: RGB  # cheek hatching and soft shadows on the skin
    lip: RGB
    line: RGB  # fine feature lines drawn ON the skin (eyelids, nose, ears, wrinkles)


def _hex(value: str) -> RGB:
    return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)


# No skin colour specified: the original neutral pencil tone. Nothing is guessed, and drawings made
# without a skin colour are byte-for-byte what renderer 1.0 produced.
NEUTRAL_SKIN = SkinPalette(skin=(234, 229, 218), shade=(205, 199, 187), lip=(176, 160, 150), line=INK_SOFT)

# value -> the colours that go with the base tone. The base tone itself comes from the vocabulary
# (``AttributeSpec.swatches``), so the colour chip in the web UI is exactly the colour that is painted.
_SKIN_TONES: dict[str, dict[str, RGB]] = {
    "white": {"shade": (222, 184, 157), "lip": (203, 126, 119), "line": (104, 80, 72)},
    "brown": {"shade": (150, 100, 66), "lip": (148, 84, 70), "line": (58, 38, 28)},
    "black": {"shade": (84, 56, 43), "lip": (138, 80, 72), "line": (26, 18, 15)},
}
_SKIN_SPEC = ATTRIBUTE_BY_KEY["skin_colour"]
SKIN_PALETTES: dict[str | None, SkinPalette] = {None: NEUTRAL_SKIN}
for _value in _SKIN_SPEC.value_keys:
    SKIN_PALETTES[_value] = SkinPalette(skin=_hex(_SKIN_SPEC.swatch_for(_value) or "#000000"), **_SKIN_TONES[_value])


# --------------------------------------------------------------------------- painter
@dataclass
class Region:
    """A clipping region built from polygons and circles (design units)."""

    polygons: list[list[Point]] = field(default_factory=list)
    circles: list[tuple[float, float, float]] = field(default_factory=list)

    def bounds(self) -> tuple[float, float, float, float]:
        xs, ys = [], []
        for poly in self.polygons:
            xs += [p[0] for p in poly]
            ys += [p[1] for p in poly]
        for x, y, r in self.circles:
            xs += [x - r, x + r]
            ys += [y - r, y + r]
        return min(xs), min(ys), max(xs), max(ys)


class Painter:
    def __init__(self, img: Image.Image | None = None, ox: int = 0, oy: int = 0, pal: SkinPalette = NEUTRAL_SKIN):
        self.img = img or Image.new("RGB", (SIZE * SS, SIZE * SS), PAPER)
        self.ox, self.oy = ox, oy
        self.pal = pal  # skin colours; sub-painters used for clipping inherit them
        self.d = ImageDraw.Draw(self.img)

    def px(self, pts: list[Point]) -> list[Point]:
        return [(x * K - self.ox, y * K - self.oy) for x, y in pts]

    def fill_all(self, color) -> None:
        self.d.rectangle((0, 0, self.img.width, self.img.height), fill=color)

    def poly(self, pts: list[Point], fill=None, outline=None, width: float = 3.0) -> None:
        if fill is not None:
            self.d.polygon(self.px(pts), fill=fill)
        if outline is not None:
            self.stroke(pts + [pts[0]], width, outline)

    def stroke(self, pts: list[Point], width: float, color) -> None:
        P = self.px(pts)
        w = max(1, round(width * K))
        self.d.line(P, fill=color, width=w, joint="curve")
        if w >= 5:  # round the ends so thick strokes have no gaps
            r = w / 2
            for x, y in (P[0], P[-1]):
                self.d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, fill=None, outline=None, width: float = 3.0) -> None:
        x0, y0 = cx * K - self.ox, cy * K - self.oy
        self.d.ellipse((x0 - rx * K, y0 - ry * K, x0 + rx * K, y0 + ry * K), fill=fill, outline=outline,
                       width=max(1, round(width * K)) if outline else 0)

    def dot(self, x: float, y: float, r: float, color) -> None:
        self.ellipse(x, y, r, r, fill=color)

    def clipped(self, region: Region, draw_fn) -> None:
        """Run ``draw_fn(sub_painter)`` but only keep what falls inside ``region`` (can be nested)."""
        if not region.polygons and not region.circles:
            return
        x0, y0, x1, y1 = region.bounds()
        bx0, by0 = max(0, int(x0 * K - self.ox) - 2), max(0, int(y0 * K - self.oy) - 2)
        bx1, by1 = min(self.img.width, int(x1 * K - self.ox) + 3), min(self.img.height, int(y1 * K - self.oy) + 3)
        if bx1 <= bx0 or by1 <= by0:
            return
        layer = self.img.crop((bx0, by0, bx1, by1))
        mask = Image.new("L", layer.size, 0)
        md = ImageDraw.Draw(mask)
        for poly in region.polygons:
            md.polygon([(x * K - self.ox - bx0, y * K - self.oy - by0) for x, y in poly], fill=255)
        for x, y, r in region.circles:
            cx, cy = x * K - self.ox - bx0, y * K - self.oy - by0
            md.ellipse((cx - r * K, cy - r * K, cx + r * K, cy + r * K), fill=255)
        draw_fn(Painter(layer, self.ox + bx0, self.oy + by0, self.pal))
        self.img.paste(layer, (bx0, by0), mask)


    def tinted(self, region: Region, color, alpha: float) -> None:
        """Blend a translucent colour over a region (used for glasses lenses)."""
        x0, y0, x1, y1 = region.bounds()
        bx0, by0 = max(0, int(x0 * K - self.ox) - 2), max(0, int(y0 * K - self.oy) - 2)
        bx1, by1 = min(self.img.width, int(x1 * K - self.ox) + 3), min(self.img.height, int(y1 * K - self.oy) + 3)
        if bx1 <= bx0 or by1 <= by0:
            return
        layer = self.img.crop((bx0, by0, bx1, by1))
        mask = Image.new("L", layer.size, 0)
        md = ImageDraw.Draw(mask)
        for poly in region.polygons:
            md.polygon([(x * K - self.ox - bx0, y * K - self.oy - by0) for x, y in poly], fill=255)
        blended = Image.blend(layer, Image.new("RGB", layer.size, color), alpha)
        self.img.paste(blended, (bx0, by0), mask)


# --------------------------------------------------------------------------- result
@dataclass
class RenderResult:
    png: bytes
    width: int
    height: int
    seed: int
    unspecified: list[str]
    notes: list[str]


# Colour only changes the palette, never the layout. Leaving it out of the seed means "make the skin darker"
# keeps every hatch stroke exactly where it was, and drawings without a colour keep their old seed.
_SEED_KEYS = tuple(k for k in ATTRIBUTE_KEYS if k != "skin_colour")


def _seed_for(attributes: Attributes) -> int:
    canonical = json.dumps({k: attributes.get(k) for k in _SEED_KEYS}, sort_keys=True)
    return int.from_bytes(hashlib.sha256(canonical.encode()).digest()[:8], "big")


# --------------------------------------------------------------------------- hair
def _hair_geometry(face: Face, length: str, style: str):
    """Returns (back_region, front_region, side_region, bun, (outer_path, front_outer, hairline_path)).

    * back  - the hair mass behind the head (and hanging down for medium / long hair)
    * front - the hair over the forehead, bounded below by the hairline
    * side  - sideburns / locks lying along the cheeks
    Tied-back hair is a tight cap plus a bun; its *length* only changes the size of the bun.
    """
    H = face.height
    tied = style == "tied_back"
    eff = "short" if tied else length
    cfg = {
        "short": dict(cut=face.eye_y + 0.03 * H, t_top=21, t_end=3, flare=0.0, end_y=None),
        "medium": dict(cut=face.mouth_y - 0.02 * H, t_top=34, t_end=56, flare=14.0, end_y=face.mouth_y + 44),
        "long": dict(cut=face.nose_y, t_top=40, t_end=76, flare=34.0, end_y=min(982.0, face.chin + 185)),
    }[eff]

    # --- back hair: the contour pushed outwards, then (for long hair) falling straight down
    pts = [p for p in face.right if p[1] <= cfg["cut"]]
    n = len(pts)
    dist = []
    for i in range(n):
        t = i / max(1, n - 1)
        dist.append(cfg["t_top"] + (cfg["t_end"] - cfg["t_top"]) * (t**1.5 if eff == "short" else t))
    outer = offset_curve(pts, dist)
    if cfg["end_y"] is not None:
        ex, ey = outer[-1]
        end_y = cfg["end_y"]
        fl = cfg["flare"]
        tail = catmull_rom(
            [(ex, ey), (ex + fl * 0.5, ey + (end_y - ey) * 0.5), (ex + fl, end_y - 6),
             (ex + fl - 20, end_y + 8), (CX + (ex + fl - CX) * 0.55, end_y + 15), (CX, end_y + 17)],
            8, start_ghost=outer[-2],
        )
        outer = outer[:-1] + tail
    if style == "wavy":
        outer = [(x + min(1.0, i / 4) * 8 * math.sin(i * 0.55), y) for i, (x, y) in enumerate(outer)]
    back = Region(polygons=[outer + mirror_x(outer)[::-1]])
    if style == "curly":  # scalloped silhouette
        for k in range(0, len(outer), 3):
            x, y = outer[k]
            r = 21 + (k % 3) * 2
            back.circles.append((x + 4, y, r))
            back.circles.append((2 * CX - x - 4, y, r))

    # --- front hair: everything above the hairline
    y_j = face.top + 0.315 * H
    top_pts = [p for p in face.right if p[1] <= y_j]
    tdist = []
    for i in range(len(top_pts)):
        t = i / max(1, len(top_pts) - 1)
        d = cfg["t_top"] * 0.9 + cfg["t_end"] * 0.35 * t
        if style == "wavy":
            d += 6 * math.sin(i * 0.55)
        tdist.append(d)
    front_outer = offset_curve(top_pts, tdist)

    ctrl = {
        "normal": [(0.0, 0.190), (0.30, 0.196), (0.60, 0.218), (0.85, 0.262), (0.97, 0.318)],
        "receding": [(0.0, 0.235), (0.25, 0.205), (0.50, 0.150), (0.72, 0.130), (0.86, 0.190), (0.97, 0.290)],
        "tied_back": [(0.0, 0.150), (0.30, 0.158), (0.60, 0.185), (0.85, 0.240), (0.97, 0.300)],
    }["receding" if style == "receding" else "tied_back" if tied else "normal"]
    hl_right = [(CX + d * face.hw(y_j), face.top + yf * H) for d, yf in ctrl]
    hl = catmull_rom(hl_right, per_segment=12, start_ghost=(2 * CX - hl_right[1][0], hl_right[1][1]))
    hairline_path = mirror_x(hl)[::-1] + hl[1:]  # left end -> centre -> right end

    # outer edge (apex -> right junction), hairline back to the left junction, left edge up to the apex
    front = Region(polygons=[front_outer + hairline_path[::-1] + mirror_x(front_outer)[::-1]])
    if style == "curly":
        for k in range(0, len(front_outer), 3):
            x, y = front_outer[k]
            front.circles.append((x + 3, y, 20))
            front.circles.append((2 * CX - x - 3, y, 20))

    # --- side hair: sideburns (short) or locks beside the cheeks (medium / long), tapering downwards
    sides = Region()
    if not tied:
        y_end = face.eye_y + 0.045 * H if eff == "short" else face.mouth_y
        width = 26 if eff == "short" else 40
        edge = [p for p in face.right if y_j - 12 <= p[1] <= y_end]
        m = len(edge)
        if m >= 3:
            inner = [(x - width * (1 - i / (m - 1)) ** 0.8 - 3, y) for i, (x, y) in enumerate(edge)]
            poly = [(x + 3, y) for x, y in edge] + inner[::-1]
            sides.polygons += [poly, mirror_x(poly)]

    bun = None
    if tied:
        r = {"short": 36, "medium": 50, "long": 64}[length]
        bun = (CX, face.top - r * 0.55 + 8, r)
    return back, front, sides, bun, (outer, front_outer, hairline_path)


def _hair_texture(rng: random.Random, p: Painter, region: Region, style: str, crown: Point, *, strokes: int = 520) -> None:
    """Fill the whole sub-painter with hair tone and hatch strokes."""
    p.fill_all(HAIR)
    x0, y0, x1, y1 = region.bounds()
    for i in range(strokes):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        color = HAIR_LIGHT if i % 6 == 0 else HAIR_DARK
        if style == "curly":
            r = rng.uniform(8, 17)
            a0 = rng.uniform(0, math.tau)
            pts = [(x + r * math.cos(a0 + s * 4.6), y + r * math.sin(a0 + s * 4.6) * 0.9) for s in
                   [k / 10 for k in range(11)]]
            p.stroke(pts, 2.1, color)
            continue
        if style == "tied_back":
            dx, dy = crown[0] - x, crown[1] - y + 40
        else:
            dx, dy = (x - crown[0]) * 0.30, 100.0
        norm = math.hypot(dx, dy) or 1.0
        dx, dy = dx / norm, dy / norm
        length = rng.uniform(46, 110)
        phase = rng.uniform(0, math.tau)
        pts = []
        for s in [k / 7 for k in range(8)]:
            lateral = 0.0
            if style == "wavy":
                lateral = 9 * math.sin(phase + s * 7.2)
            pts.append((x + dx * s * length - dy * lateral, y + dy * s * length + dx * lateral))
        p.stroke(pts, 2.2, color)


# --------------------------------------------------------------------------- body parts
def _draw_bust(p: Painter, face: Face, gender: str | None) -> None:
    neck_hw = {"male": 92, "female": 70}.get(gender or "", 80)
    y0 = face.chin - 110
    top = face.chin + 92  # where the shoulders start
    neck = [(CX - neck_hw, y0), (CX + neck_hw, y0), (CX + neck_hw * 1.1, top + 20), (CX + neck_hw * 1.25, 1000),
            (CX - neck_hw * 1.25, 1000), (CX - neck_hw * 1.1, top + 20)]
    p.poly(neck, fill=p.pal.skin)
    for side in (1, -1):
        p.stroke([(CX + side * neck_hw, y0 + 20), (CX + side * neck_hw * 1.1, top + 20)], 3, p.pal.line)
    shoulder_r = catmull_rom(
        [(CX + neck_hw * 1.1, top - 8), (CX + 200, top + 14), (CX + 340, top + 70), (CX + 440, top + 170), (CX + 480, 1000)],
        8, start_ghost=(CX + neck_hw * 0.9, top - 30),
    )
    garment = shoulder_r + [(CX + 480, 1000), (CX - 480, 1000)] + mirror_x(shoulder_r)[::-1]
    p.poly(garment, fill=GARMENT)
    p.stroke(shoulder_r, 3, INK_SOFT)
    p.stroke(mirror_x(shoulder_r), 3, INK_SOFT)
    neckline = catmull_rom([(CX - neck_hw * 1.15, top - 6), (CX, top + 62), (CX + neck_hw * 1.15, top - 6)], 10)
    p.stroke(neckline, 3, INK_SOFT)


def _draw_ears(p: Painter, face: Face) -> None:
    y = (face.brow_y + face.nose_y) / 2 + 6
    hw = face.hw(y)
    for side in (1, -1):
        cx = CX + side * (hw + 12)
        p.ellipse(cx, y, 26, 62, fill=p.pal.skin, outline=INK, width=3.2)
        inner = [(cx + side * (-4), y - 34), (cx + side * 8, y - 8), (cx + side * 2, y + 26)]
        p.stroke(catmull_rom(inner, 6), 2.4, p.pal.line)


def _draw_face_base(p: Painter, face: Face, rng: random.Random) -> None:
    outline = face.outline()
    p.poly(outline, fill=p.pal.skin)
    # soft cheek / jaw hatching (pencil feel)
    shade_region = Region(polygons=[outline])

    def shade(sub: Painter) -> None:
        for _ in range(70):
            x = rng.uniform(CX + 0.35 * face.hw(face.eye_y), CX + face.hw(face.eye_y) + 12)
            y = rng.uniform(face.eye_y + 0.05 * face.height, face.chin - 20)
            sub.stroke([(x, y), (x - 14, y + 26)], 1.6, sub.pal.shade)
        for _ in range(40):  # under the jaw
            x = rng.uniform(CX - 120, CX + 120)
            y = rng.uniform(face.chin - 38, face.chin - 4)
            sub.stroke([(x, y), (x - 10, y + 14)], 1.6, sub.pal.shade)

    p.clipped(shade_region, shade)
    p.stroke(outline + [outline[0]], 3.6, INK)


def _lerp_pts(pts: list[tuple[float, float]], w: float, cx: float, cy: float, side: int) -> list[Point]:
    return [(cx + side * x * w, cy + y * w) for x, y in pts]


EYE_SHAPES = {
    "almond": dict(
        upper=[(-0.5, 0.03), (-0.28, -0.11), (0.0, -0.19), (0.28, -0.13), (0.5, -0.02)],
        lower=[(0.5, -0.02), (0.30, 0.07), (0.0, 0.11), (-0.28, 0.09), (-0.5, 0.03)],
    ),
    "round": dict(
        upper=[(-0.40, 0.0), (-0.27, -0.23), (0.0, -0.33), (0.27, -0.23), (0.40, 0.0)],
        lower=[(0.40, 0.0), (0.27, 0.23), (0.0, 0.33), (-0.27, 0.23), (-0.40, 0.0)],
    ),
    "narrow": dict(
        upper=[(-0.5, 0.01), (-0.28, -0.075), (0.0, -0.105), (0.28, -0.075), (0.5, 0.0)],
        lower=[(0.5, 0.0), (0.28, 0.05), (0.0, 0.07), (-0.28, 0.055), (-0.5, 0.01)],
    ),
    "droopy": dict(
        upper=[(-0.5, -0.02), (-0.28, -0.14), (0.0, -0.17), (0.3, -0.05), (0.5, 0.13)],
        lower=[(0.5, 0.13), (0.3, 0.13), (0.0, 0.11), (-0.28, 0.07), (-0.5, -0.02)],
    ),
}


def _draw_eye(p: Painter, cx: float, cy: float, w: float, shape: str | None, side: int, female: bool) -> None:
    spec = EYE_SHAPES.get(shape or "almond", EYE_SHAPES["almond"])
    # inner corner is nearest the centre line: for the right-hand eye x grows outward
    upper = catmull_rom(_lerp_pts(spec["upper"], w, cx, cy, side), 8)
    lower = catmull_rom(_lerp_pts(spec["lower"], w, cx, cy, side), 8)
    shape_pts = upper + lower
    p.poly(shape_pts, fill=EYE_WHITE)
    iris_r = {"round": 0.20, "narrow": 0.17, "droopy": 0.18}.get(shape or "", 0.18) * w
    region = Region(polygons=[shape_pts])

    def iris(sub: Painter) -> None:
        ix, iy = cx + side * 0.02 * w, cy - 0.02 * w
        sub.dot(ix, iy, iris_r, INK_SOFT)
        sub.dot(ix, iy, iris_r * 0.55, INK)
        sub.dot(ix - iris_r * 0.28, iy - iris_r * 0.30, iris_r * 0.18, EYE_WHITE)

    p.clipped(region, iris)
    p.stroke(upper, 4.2, INK)
    p.stroke(lower, 2.4, p.pal.line)
    if shape != "narrow":  # eyelid crease
        crease = [(x, y - 0.075 * w) for x, y in upper[3:-3]]
        p.stroke(crease, 1.8, p.pal.line)
    if shape == "droopy":  # heavy lid and a bag underneath
        lid = [(x, y - 0.07 * w) for x, y in upper[2:-2]]
        p.stroke(lid, 2.4, p.pal.line)
        bag = catmull_rom(_lerp_pts([(-0.42, 0.20), (-0.1, 0.27), (0.3, 0.26), (0.5, 0.2)], w, cx, cy, side), 6)
        p.stroke(bag, 2.0, p.pal.line)
    if female:  # a few lash strokes on the outer upper lid
        for k in range(3):
            bx, by = upper[len(upper) - 2 - k]
            p.stroke([(bx, by), (bx + side * (5 + 2 * k), by - 9 - k * 2)], 2.2, INK)


BROW_THICKNESS = {"thin": 4.0, "medium": 9.0, "thick": 17.0}


def _draw_brow(p: Painter, rng: random.Random, cx: float, y: float, w: float, thickness: str | None, side: int) -> None:
    t = BROW_THICKNESS.get(thickness or "medium", 9.0)
    arc = catmull_rom(_lerp_pts([(-0.62, 0.03), (-0.25, -0.07), (0.20, -0.11), (0.62, -0.05), (0.78, 0.04)], w, cx, y, side), 8)
    n = len(arc)
    upper, lower = [], []
    for i, (x, yy) in enumerate(arc):
        s = i / (n - 1)
        th = t * (0.45 + 0.55 * math.sin(math.pi * min(1.0, 0.18 + 0.82 * s)))
        upper.append((x, yy - th / 2))
        lower.append((x, yy + th / 2))
    p.poly(upper + lower[::-1], fill=HAIR_DARK)
    if thickness == "thick":  # bushy: stray hair strokes above and below the shape
        for _ in range(16):
            i = rng.randrange(2, n - 2)
            x, yy = arc[i]
            p.stroke([(x, yy - t / 2), (x + side * rng.uniform(2, 9), yy - t / 2 - rng.uniform(4, 9))], 2.0, HAIR_DARK)
            p.stroke([(x, yy + t / 2), (x + side * rng.uniform(2, 9), yy + t / 2 + rng.uniform(3, 6))], 2.0, HAIR_DARK)


NOSE_SHAPES = {
    "narrow": dict(bridge=16, base=32, tip=0, nostril=10, up=0, hook=0),
    "broad": dict(bridge=30, base=62, tip=2, nostril=21, up=0, hook=0),
    "pointed": dict(bridge=18, base=29, tip=20, nostril=9, up=0, hook=0),
    "flat": dict(bridge=24, base=56, tip=-6, nostril=20, up=0, hook=0),
    "hooked": dict(bridge=19, base=32, tip=30, nostril=8, up=0, hook=1),
    "upturned": dict(bridge=17, base=36, tip=-6, nostril=14, up=24, hook=0),
    None: dict(bridge=20, base=38, tip=4, nostril=12, up=0, hook=0),
}


def _draw_nose(p: Painter, face: Face, shape: str | None) -> None:
    s = NOSE_SHAPES.get(shape, NOSE_SHAPES[None])
    y_top = face.eye_y + 0.035 * face.height
    y_base = face.nose_y
    bridge, base = s["bridge"], s["base"]
    flat_len = 0.45 if shape == "flat" else 1.0
    nostril_ry = s["nostril"] * (0.8 if s["up"] else 0.5)
    for side in (1, -1):
        bx0 = CX + side * bridge * 0.78
        by0 = y_top + (1 - flat_len) * (y_base - y_top) * 0.9
        side_line = catmull_rom([(bx0, by0), (CX + side * (bridge * 0.95 + (base - bridge) * 0.45), (by0 + y_base) / 2 + 6),
                                 (CX + side * base * 0.92, y_base - 14)], 8)
        p.stroke(side_line, 2.8, p.pal.line)
        wing = catmull_rom([(CX + side * base * 0.92, y_base - 14), (CX + side * (base + 3), y_base + 1),
                            (CX + side * base * 0.72, y_base + 12), (CX + side * base * 0.40, y_base + 11)], 8)
        p.stroke(wing, 3.2, INK)
        p.ellipse(CX + side * base * 0.5, y_base + 7 + s["up"] * 0.2, s["nostril"], nostril_ry, fill=INK)
    tip_y = y_base + 14 + s["tip"]
    base_pts = catmull_rom([(CX - base * 0.42, y_base + 10), (CX, tip_y - s["up"] * 0.6), (CX + base * 0.42, y_base + 10)], 8)
    p.stroke(base_pts, 3.0, p.pal.line)
    if shape in ("pointed", "hooked"):  # a clear, pointed tip
        p.stroke([(CX - 11, tip_y - 9), (CX, tip_y + 6), (CX + 11, tip_y - 9)], 2.8, INK)
    if s["up"]:  # upturned: the tip is lifted - show it with a short arc above the nostrils
        p.stroke(catmull_rom([(CX - 14, y_base - 4), (CX, y_base - 10), (CX + 14, y_base - 4)], 6), 2.4, p.pal.line)
    # soft shadow down the right side of the bridge
    shade = [(CX + bridge * 1.0, y_top + 30), (CX + bridge * 1.35 + 4, (y_top + y_base) / 2), (CX + base * 0.95, y_base - 12)]
    if s["hook"]:  # hooked: a shaded plane on the right of the bridge ending in a drooping tip
        plane = catmull_rom([(CX + bridge * 0.9, y_top + (y_base - y_top) * 0.30), (CX + bridge * 1.7, y_top + (y_base - y_top) * 0.62),
                             (CX + bridge * 0.8, tip_y - 3)], 8)
        p.stroke(plane, 6.0, p.pal.shade)
        p.stroke(plane, 2.2, p.pal.line)
    else:
        p.stroke(catmull_rom(shade, 6), 5.0, p.pal.shade)


MOUTH_SHAPES = {
    "thin": dict(mw=52, tu=7, tl=10, corner=0),
    "full": dict(mw=58, tu=21, tl=31, corner=0),
    "wide": dict(mw=84, tu=12, tl=18, corner=0),
    "small": dict(mw=36, tu=9, tl=13, corner=0),
    "downturned": dict(mw=56, tu=10, tl=14, corner=17),
    None: dict(mw=54, tu=11, tl=16, corner=0),
}


def _mouth_outline(face: Face, shape: str | None):
    s = MOUTH_SHAPES.get(shape, MOUTH_SHAPES[None])
    y, mw, tu, tl, c = face.mouth_y, s["mw"], s["tu"], s["tl"], s["corner"]
    line = catmull_rom([(CX - mw, y + c), (CX - mw * 0.5, y + 1 + c * 0.2), (CX, y), (CX + mw * 0.5, y + 1 + c * 0.2),
                        (CX + mw, y + c)], 8)
    upper_edge = catmull_rom([(CX - mw, y + c), (CX - mw * 0.55, y - tu * 0.75 + c * 0.45), (CX - mw * 0.18, y - tu),
                              (CX, y - tu * 0.68), (CX + mw * 0.18, y - tu), (CX + mw * 0.55, y - tu * 0.75 + c * 0.45),
                              (CX + mw, y + c)], 6)
    lower_edge = catmull_rom([(CX + mw, y + c), (CX + mw * 0.5, y + tl * 0.75 + c * 0.4), (CX, y + tl),
                              (CX - mw * 0.5, y + tl * 0.75 + c * 0.4), (CX - mw, y + c)], 8)
    return line, upper_edge, lower_edge, s


def _draw_mouth(p: Painter, face: Face, shape: str | None, clear_patch: bool) -> None:
    line, upper_edge, lower_edge, s = _mouth_outline(face, shape)
    if clear_patch:  # a skin-coloured opening so a beard does not cover the lips
        p.ellipse(CX, face.mouth_y + 4, s["mw"] + 16, s["tl"] + s["tu"] + 22, fill=p.pal.skin)
    p.poly(upper_edge + line[::-1], fill=p.pal.lip)
    p.poly(lower_edge + line, fill=p.pal.lip)
    p.stroke(upper_edge, 2.6, p.pal.line)
    p.stroke(lower_edge, 2.6, p.pal.line)
    p.stroke(line, 5.0, INK)
    # chin shadow under the lower lip
    y = face.mouth_y + s["tl"] + 16
    p.stroke(catmull_rom([(CX - 24, y), (CX, y + 5), (CX + 24, y)], 6), 1.8, p.pal.shade)


# --------------------------------------------------------------------------- facial hair
def _beard_region(face: Face) -> Region:
    y_start = face.eye_y + 0.15 * face.height
    edge = [p for p in face.right if p[1] >= y_start]
    dist = [10 + 6 * (i / max(1, len(edge) - 1)) for i in range(len(edge))]
    outer = offset_curve(edge, dist)
    outer_all = outer + mirror_x(outer)[::-1]
    hw_s = face.hw(y_start)
    ny = face.nose_y + 0.012 * face.height
    inner_right = [(CX + hw_s * 0.84, y_start - 4), (CX + hw_s * 0.74, y_start + 0.10 * face.height),
                   (CX + 0.42 * face.hw(ny), ny + 8), (CX + 20, ny + 3), (CX, ny)]
    inner = catmull_rom(inner_right, 8, start_ghost=(CX + hw_s * 0.9, y_start - 20))
    inner_path = mirror_x(inner) + inner[::-1][1:]  # `inner` runs ear -> centre, so: left ear -> centre -> right ear
    return Region(polygons=[outer_all + inner_path])


def _hair_strokes_in(rng: random.Random, sub: Painter, region: Region, *, count: int, mode: str) -> None:
    x0, y0, x1, y1 = region.bounds()
    for i in range(count):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        color = HAIR_LIGHT if i % 7 == 0 else HAIR_DARK
        if mode == "beard":
            dx = (x - CX) * 0.004 + rng.uniform(-0.25, 0.25)
            pts = [(x + dx * s * 40, y + s * rng.uniform(26, 44)) for s in (0.0, 0.5, 1.0)]
        else:  # mustache: strokes sweep outward from the centre
            sgn = 1 if x >= CX else -1
            pts = [(x, y), (x + sgn * 16, y + 10)]
        sub.stroke(pts, 2.2, color)


def _draw_beard(p: Painter, face: Face, rng: random.Random) -> None:
    region = _beard_region(face)
    p.clipped(region, lambda sub: (sub.fill_all(HAIR), _hair_strokes_in(rng, sub, region, count=900, mode="beard")))
    for poly in region.polygons:
        p.stroke(poly + [poly[0]], 2.4, INK_SOFT)


def _draw_stubble(p: Painter, face: Face, rng: random.Random) -> None:
    y_start = face.eye_y + 0.15 * face.height
    lower_face = _beard_region(face)
    face_region = Region(polygons=[face.outline()])

    def dots(sub: Painter) -> None:
        for _ in range(1500):
            sub.dot(rng.uniform(CX - 270, CX + 270), rng.uniform(y_start, face.chin), 1.5, INK_SOFT)

    # stubble only where the face outline AND the lower-face area overlap
    p.clipped(face_region, lambda inner: inner.clipped(lower_face, dots))


def _draw_mustache(p: Painter, face: Face, rng: random.Random, *, small: bool = False) -> None:
    mw = 44 if small else 72
    y_top = face.nose_y + 15
    y_mouth = face.mouth_y
    top = catmull_rom([(CX - mw * 1.18, y_mouth + 10), (CX - mw * 0.55, y_mouth - 20), (CX, y_top + 9),
                       (CX + mw * 0.55, y_mouth - 20), (CX + mw * 1.18, y_mouth + 10)], 8)
    bottom = catmull_rom([(CX + mw * 1.18, y_mouth + 10), (CX + mw * 0.6, y_mouth - 9), (CX, y_mouth - 11),
                          (CX - mw * 0.6, y_mouth - 9), (CX - mw * 1.18, y_mouth + 10)], 8)
    region = Region(polygons=[top + bottom])
    p.clipped(region, lambda sub: (sub.fill_all(HAIR), _hair_strokes_in(rng, sub, region, count=160, mode="mustache")))
    p.stroke(top + bottom + [top[0]], 2.2, INK_SOFT)


def _draw_goatee(p: Painter, face: Face, rng: random.Random) -> None:
    y0 = face.mouth_y + 34
    patch = catmull_rom([(CX - 52, y0), (CX - 58, y0 + 40), (CX - 36, face.chin - 14), (CX, face.chin + 4),
                         (CX + 36, face.chin - 14), (CX + 58, y0 + 40), (CX + 52, y0)], 8)
    ring = catmull_rom([(CX + 52, y0), (CX, y0 - 6), (CX - 52, y0)], 6)
    region = Region(polygons=[patch + ring])
    p.clipped(region, lambda sub: (sub.fill_all(HAIR), _hair_strokes_in(rng, sub, region, count=260, mode="beard")))
    p.stroke(patch + ring + [patch[0]], 2.4, INK_SOFT)
    _draw_mustache(p, face, rng, small=True)


def _rounded_rect(cx: float, cy: float, w: float, h: float, r: float, steps: int = 7) -> list[Point]:
    pts: list[Point] = []
    for ccx, ccy, start in (
        (cx + w / 2 - r, cy - h / 2 + r, -90),
        (cx + w / 2 - r, cy + h / 2 - r, 0),
        (cx - w / 2 + r, cy + h / 2 - r, 90),
        (cx - w / 2 + r, cy - h / 2 + r, 180),
    ):
        for k in range(steps + 1):
            a = math.radians(start + 90 * k / steps)
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return pts


def _draw_glasses(p: Painter, face: Face) -> None:
    w = face.eye_w * 1.5
    h = w * 0.80
    for side in (1, -1):
        cx, cy = CX + side * face.eye_dx, face.eye_y
        lens = _rounded_rect(cx, cy, w, h, h * 0.32)
        p.tinted(Region(polygons=[lens]), LENS, 0.22)
        p.poly(lens, outline=INK, width=5.0)
        arm_end = (CX + side * (face.hw(cy) + 26), cy - 4)  # temple arm running back to the ear
        p.stroke([(cx + side * w / 2, cy - h * 0.30), arm_end], 4.2, INK)
    inner_l, inner_r = CX - face.eye_dx + w / 2, CX + face.eye_dx - w / 2
    p.stroke(catmull_rom([(inner_l, face.eye_y - h * 0.14), (CX, face.eye_y - h * 0.28), (inner_r, face.eye_y - h * 0.14)], 8), 4.4, INK)


def _draw_age_lines(p: Painter, face: Face, age: str | None) -> None:
    if age in (None, "young_adult"):
        return
    level = {"adult": 1, "middle_aged": 2, "elderly": 3}[age]
    hw = face.hw(face.eye_y)
    nose_hw = 38
    # nasolabial folds: nose wings to mouth corners
    for side in (1, -1):
        fold = catmull_rom([(CX + side * (nose_hw + 8), face.nose_y + 4),
                            (CX + side * (nose_hw + 22 + level * 3), (face.nose_y + face.mouth_y) / 2 + 8),
                            (CX + side * (54 + level * 4), face.mouth_y + 8)], 6)
        p.stroke(fold, 1.4 + level * 0.5, p.pal.shade if level == 1 else p.pal.line)
    if level >= 2:  # forehead lines and crow's feet
        for k in range(level):
            y = face.brow_y - 46 - k * 22
            p.stroke(catmull_rom([(CX - 120, y + 4), (CX, y - 3), (CX + 120, y + 4)], 8), 1.8, p.pal.shade if level == 2 else p.pal.line)
        for side in (1, -1):
            ex = CX + side * (face.eye_dx + face.eye_w / 2 + 6)
            for k in range(level):
                p.stroke([(ex, face.eye_y + (k - 1) * 11), (ex + side * (22 + k * 3), face.eye_y + (k - 1) * 18)], 1.8, p.pal.line)
    if level >= 3:  # eye bags, cheek hollows, chin line
        for side in (1, -1):
            cx = CX + side * face.eye_dx
            p.stroke(catmull_rom([(cx - 38, face.eye_y + 30), (cx, face.eye_y + 40), (cx + 38, face.eye_y + 30)], 6), 1.8, p.pal.line)
            hollow = catmull_rom([(CX + side * (hw * 0.78), face.eye_y + 80), (CX + side * (hw * 0.62), face.nose_y + 10),
                                  (CX + side * (hw * 0.50), face.mouth_y + 30)], 6)
            p.stroke(hollow, 1.6, p.pal.shade)
        p.stroke(catmull_rom([(CX - 40, face.chin - 52), (CX, face.chin - 46), (CX + 40, face.chin - 52)], 6), 1.6, p.pal.line)


# --------------------------------------------------------------------------- main entry
def render_schematic(attributes: Attributes) -> RenderResult:
    seed = _seed_for(attributes)
    rng = random.Random(seed)
    notes: list[str] = []
    a = {k: attributes.get(k) for k in ATTRIBUTE_KEYS}
    unspecified = [k for k in ATTRIBUTE_KEYS if not a[k]]

    gender = a["apparent_gender"]
    jaw_scale = {"male": 1.03, "female": 0.95}.get(gender or "", 1.0)
    face = build_face(a["face_shape"], jaw_scale=jaw_scale)
    p = Painter(pal=SKIN_PALETTES[a["skin_colour"]])

    # --- hair (back layer) --------------------------------------------------------------
    length = a["hair_length"] or "short"
    style = a["hair_style"] or "straight"
    has_hair = length != "bald"
    if not has_hair and a["hair_style"]:
        notes.append("Hair style was ignored because the hair length is 'bald'.")
    hair = None
    if has_hair:
        hair = _hair_geometry(face, length, style)
        back, front, sides, bun, outlines = hair
        crown = (CX, face.top - 30)
        if bun:
            bx, by, br = bun
            bun_region = Region(circles=[(bx, by, br)])
            p.clipped(bun_region, lambda sub: _hair_texture(rng, sub, bun_region, "curly", crown, strokes=60))
            p.ellipse(bx, by, br, br, outline=INK_SOFT, width=2.6)
            p.stroke([(bx - br * 0.7, by + br * 0.92), (bx + br * 0.7, by + br * 0.92)], 6, INK)
        back_region = back
        p.clipped(back_region, lambda sub: _hair_texture(rng, sub, back_region, style, crown))
        outer = outlines[0]
        if style != "curly":
            p.stroke(outer, 3.0, INK_SOFT)
            p.stroke(mirror_x(outer), 3.0, INK_SOFT)

    # --- body, ears, face --------------------------------------------------------------------------
    _draw_bust(p, face, gender)
    covered_ears = has_hair and length in ("medium", "long") and style != "tied_back"
    if not covered_ears:
        _draw_ears(p, face)
    _draw_face_base(p, face, rng)
    _draw_age_lines(p, face, a["age_description"])

    # --- facial hair that sits under the mouth ------------------------------------------------------------
    facial = a["facial_hair"]
    if facial == "beard":
        _draw_beard(p, face, rng)
    elif facial == "stubble":
        _draw_stubble(p, face, rng)
    elif facial == "goatee":
        pass  # drawn after the mouth so it sits on top

    # --- features ----------------------------------------------------------------------------------------------
    female = gender == "female"
    eye_w = face.eye_w
    for side in (1, -1):
        cx = CX + side * face.eye_dx
        _draw_eye(p, cx, face.eye_y, eye_w, a["eye_shape"], side, female)
        _draw_brow(p, rng, cx, face.brow_y, eye_w, a["eyebrows"], side)
    _draw_nose(p, face, a["nose_shape"])
    _draw_mouth(p, face, a["mouth_shape"], clear_patch=facial in ("beard", "goatee"))
    if facial == "mustache":
        _draw_mustache(p, face, rng)
    elif facial == "goatee":
        _draw_goatee(p, face, rng)
    elif facial == "beard":
        _draw_mustache(p, face, rng)

    # --- hair (front layer) -----------------------------------------------------------------------------------------
    if has_hair and hair is not None:
        back, front, sides, bun, outlines = hair
        crown = (CX, face.top - 30)
        p.clipped(front, lambda sub: _hair_texture(rng, sub, front, style, crown, strokes=420))
        if sides.polygons:
            p.clipped(sides, lambda sub: _hair_texture(rng, sub, sides, style, crown, strokes=130))
        _, front_outer, hairline_path = outlines
        p.stroke(front_outer, 3.0, INK_SOFT)
        p.stroke(mirror_x(front_outer), 3.0, INK_SOFT)
        p.stroke(hairline_path, 2.6, INK)

    if a["glasses"] == "glasses":
        _draw_glasses(p, face)

    # --- finish ----------------------------------------------------------------------------------------------------------
    img = p.img.resize((SIZE, SIZE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", compress_level=6)
    return RenderResult(png=buf.getvalue(), width=SIZE, height=SIZE, seed=seed, unspecified=unspecified, notes=notes)
