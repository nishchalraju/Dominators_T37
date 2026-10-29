"""The schematic renderer must make every attribute visible - otherwise "revisions" would be cosmetic."""

import hashlib
import io

import pytest
from PIL import Image, ImageChops

from app.services.attributes import ATTRIBUTE_BY_KEY, ATTRIBUTES
from app.services.sketch_models.schematic_renderer import PAPER, SKIN_PALETTES, render_schematic

BASE = {"apparent_gender": "male", "age_description": "adult", "face_shape": "oval", "hair_length": "short", "hair_style": "straight",
        "eyebrows": "medium", "eye_shape": "almond", "nose_shape": "narrow", "mouth_shape": "thin", "facial_hair": "none", "glasses": "none"}  # fmt: skip


def image(attrs, *, colour=False):
    img = Image.open(io.BytesIO(render_schematic(attrs).png))
    return img.convert("RGB") if colour else img.convert("L")


def summed_difference(a, b):
    r, g, bl = ImageChops.difference(a, b).split()
    return ImageChops.add(ImageChops.add(r, g), bl)


def changed_pixels(a, b) -> int:
    if a.mode == "RGB":  # a colour change is mostly hue; a grey-scale comparison would call it "no change"
        return summed_difference(a, b).point(lambda v: 255 if v > 30 else 0).histogram()[255]
    diff = ImageChops.difference(a, b).point(lambda v: 255 if v > 24 else 0)
    return diff.histogram()[255]


def chip_rgb(value: str) -> tuple[int, int, int]:
    chip = ATTRIBUTE_BY_KEY["skin_colour"].swatch_for(value)
    return int(chip[1:3], 16), int(chip[3:5], 16), int(chip[5:7], 16)


def pixel_counts(img) -> dict:
    return {colour: n for n, colour in img.getcolors(maxcolors=1_100_000)}


def test_output_is_a_valid_1024_png():
    r = render_schematic(BASE)
    img = Image.open(io.BytesIO(r.png))
    assert img.format == "PNG" and img.size == (1024, 1024) and r.width == r.height == 1024


def test_rendering_is_deterministic():
    assert hashlib.sha256(render_schematic(BASE).png).digest() == hashlib.sha256(render_schematic(BASE).png).digest()


@pytest.mark.parametrize("spec", ATTRIBUTES, ids=lambda s: s.key)
def test_every_value_of_every_attribute_changes_the_picture(spec):
    colour = spec.key == "skin_colour"
    base_img = image(BASE, colour=colour)
    for value in spec.value_keys:
        if BASE.get(spec.key) == value:
            continue
        attrs = {**BASE, spec.key: value}
        if spec.key == "hair_style":
            attrs["hair_length"] = "medium"  # style is only visible when there is hair
            reference = image({**BASE, "hair_length": "medium"})
        else:
            reference = base_img
        assert changed_pixels(reference, image(attrs, colour=colour)) > 300, f"{spec.key}={value} did not visibly change the drawing"


def test_hair_style_is_ignored_for_a_bald_head_and_says_so():
    r = render_schematic({**BASE, "hair_length": "bald", "hair_style": "curly"})
    assert any("bald" in n for n in r.notes)


def test_unspecified_attributes_are_reported():
    r = render_schematic({"face_shape": "round"})
    assert "glasses" in r.unspecified and "face_shape" not in r.unspecified


def test_empty_attributes_still_render_a_neutral_face():
    assert len(render_schematic({}).png) > 10_000


# ----------------------------------------------------------------------------- skin colour
@pytest.mark.parametrize("value", ATTRIBUTE_BY_KEY["skin_colour"].value_keys)
def test_the_face_is_painted_in_exactly_the_colour_of_the_chip_the_ui_shows(value):
    counts = pixel_counts(image({**BASE, "skin_colour": value}, colour=True))
    assert counts.get(chip_rgb(value), 0) > 100_000  # face, neck and ears


def test_every_skin_colour_value_has_a_palette():
    assert set(SKIN_PALETTES) == {None, *ATTRIBUTE_BY_KEY["skin_colour"].value_keys}


def test_without_a_skin_colour_the_neutral_tone_is_used_and_no_chip_colour_appears():
    counts = pixel_counts(image(BASE, colour=True))
    assert counts.get((234, 229, 218), 0) > 100_000
    assert all(counts.get(chip_rgb(v), 0) == 0 for v in ATTRIBUTE_BY_KEY["skin_colour"].value_keys)


def test_the_three_skin_colours_are_clearly_different_from_each_other():
    imgs = {v: image({**BASE, "skin_colour": v}, colour=True) for v in ("white", "brown", "black")}
    assert changed_pixels(imgs["white"], imgs["brown"]) > 100_000
    assert changed_pixels(imgs["brown"], imgs["black"]) > 100_000
    assert changed_pixels(imgs["white"], imgs["black"]) > 100_000


def test_colour_changes_only_the_colours_never_the_layout():
    """"Make the skin darker" must not move a single hair stroke or feature."""
    assert render_schematic(BASE).seed == render_schematic({**BASE, "skin_colour": "black"}).seed

    def silhouette(attrs):
        return summed_difference(image(attrs, colour=True), Image.new("RGB", (1024, 1024), PAPER)).point(lambda v: 255 if v > 30 else 0)

    white, black = silhouette({**BASE, "skin_colour": "white"}), silhouette({**BASE, "skin_colour": "black"})
    assert ImageChops.difference(white, black).histogram()[255] < 1_000  # only anti-aliased edge pixels differ
    other_layout = silhouette({**BASE, "skin_colour": "white", "face_shape": "round"})  # the test can fail: a real change is huge
    assert ImageChops.difference(white, other_layout).histogram()[255] > 20_000


def test_unspecified_skin_colour_is_reported_so_the_neutral_tone_is_never_passed_off_as_a_choice():
    assert "skin_colour" in render_schematic(BASE).unspecified
    assert "skin_colour" not in render_schematic({**BASE, "skin_colour": "brown"}).unspecified
