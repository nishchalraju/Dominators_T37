"""Image helpers: validation, safe re-encoding, thumbnails and the provenance caption band.

Every image that enters the system (an AI model's output or a user upload) goes through
``normalize_to_png``: it is decoded, checked, stripped of metadata (EXIF can hold GPS
data) and re-encoded as a plain RGB PNG. Stored files are therefore always clean PNGs.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}
FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"

# Colours of the caption band (matches the dark UI, readable when printed)
BAND_BG = (17, 26, 43)
BAND_FG = (230, 237, 247)
BAND_ACCENT = (34, 211, 238)
BAND_WARN = (251, 191, 36)


class ImageValidationError(ValueError):
    """The bytes are not an acceptable image (message is safe to show to the user)."""


@dataclass(frozen=True)
class ImageInfo:
    format: str
    width: int
    height: int
    size_bytes: int
    sha256: str


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect_image(data: bytes, *, max_pixels: int = 25_000_000, max_bytes: int | None = None) -> ImageInfo:
    """Check that ``data`` is a real PNG / JPEG / WebP of reasonable size. Never trusts file names."""
    if not data:
        raise ImageValidationError("The image is empty.")
    if max_bytes is not None and len(data) > max_bytes:
        raise ImageValidationError(f"The image is larger than the {max_bytes // (1024 * 1024)} MB limit.")
    try:
        with Image.open(io.BytesIO(data)) as img:  # reads only the header
            fmt = (img.format or "").upper()
            width, height = img.size
            if fmt not in ALLOWED_FORMATS:
                raise ImageValidationError("Only PNG, JPEG and WebP images are accepted.")
            if width < 16 or height < 16:
                raise ImageValidationError("The image is too small (minimum 16 x 16 pixels).")
            if width * height > max_pixels:
                raise ImageValidationError("The image has too many pixels.")
            img.verify()  # detects truncated / corrupt files
    except ImageValidationError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
        raise ImageValidationError("The file is not a valid image.") from exc
    return ImageInfo(format=fmt, width=width, height=height, size_bytes=len(data), sha256=sha256_hex(data))


def normalize_to_png(data: bytes, *, max_pixels: int = 25_000_000, max_side: int = 2048) -> bytes:
    """Decode, flatten transparency onto white, drop metadata, shrink if huge, re-encode as PNG."""
    inspect_image(data, max_pixels=max_pixels)
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            if img.mode in ("RGBA", "LA", "P"):
                rgba = img.convert("RGBA")
                flat = Image.new("RGB", rgba.size, (255, 255, 255))
                flat.paste(rgba, mask=rgba.split()[-1])
                rgb = flat
            else:
                rgb = img.convert("RGB")
    except (OSError, ValueError) as exc:
        raise ImageValidationError("The file is not a valid image.") from exc
    if max(rgb.size) > max_side:
        scale = max_side / max(rgb.size)
        rgb = rgb.resize((max(1, round(rgb.width * scale)), max(1, round(rgb.height * scale))), Image.LANCZOS)
    buf = io.BytesIO()
    rgb.save(buf, format="PNG", compress_level=6)  # no EXIF / text chunks are written
    return buf.getvalue()


def pil_to_png(img: Image.Image, **kwargs) -> bytes:
    """Encode a PIL image (for example returned by a model client) through the same safe path."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return normalize_to_png(buf.getvalue(), **kwargs)


def thumbnail_png(png: bytes, side: int = 320) -> bytes:
    with Image.open(io.BytesIO(png)) as img:
        img = img.convert("RGB")
        img.thumbnail((side, side), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", compress_level=6)
        return buf.getvalue()


# --------------------------------------------------------------------------- caption band
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    name = "NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf"
    try:
        return ImageFont.truetype(str(FONT_DIR / name), size)
    except OSError:  # font missing: fall back to Pillow's built-in bitmap font
        return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def add_provenance_band(png: bytes, headline: str, lines: list[str], *, warning: bool = False) -> bytes:
    """Return a copy of ``png`` with a caption band underneath stating how the image was made.

    The stored sketch stays clean; only downloads and reports carry the band, so the
    provenance statement cannot be cropped away by accident when sharing the file.
    """
    with Image.open(io.BytesIO(png)) as src:
        base = src.convert("RGB")
    width = base.width
    scale = max(1.0, width / 1024)
    f_head, f_body = _font(round(26 * scale), bold=True), _font(round(19 * scale))
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    pad = round(18 * scale)
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(_wrap(probe, line, f_body, width - 2 * pad))
    line_h = round(27 * scale)
    band_h = pad * 2 + round(34 * scale) + line_h * len(wrapped)

    out = Image.new("RGB", (width, base.height + band_h), BAND_BG)
    out.paste(base, (0, 0))
    d = ImageDraw.Draw(out)
    y = base.height + pad
    d.text((pad, y), headline, font=f_head, fill=BAND_WARN if warning else BAND_ACCENT)
    y += round(36 * scale)
    for line in wrapped:
        d.text((pad, y), line, font=f_body, fill=BAND_FG)
        y += line_h
    buf = io.BytesIO()
    out.save(buf, format="PNG", compress_level=6)
    return buf.getvalue()
