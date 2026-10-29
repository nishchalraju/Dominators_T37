import re

import pytest

from app.services.attributes import (
    ATTRIBUTE_BY_KEY,
    ATTRIBUTE_KEYS,
    ATTRIBUTES,
    STEP_BASELINES,
    VOCABULARY_VERSION,
    AttributeValidationError,
    attribute_diff,
    clean_attributes,
    meta_payload,
)


def test_vocabulary_has_twelve_attributes_with_unique_values():
    assert len(ATTRIBUTE_KEYS) == 12
    for spec in ATTRIBUTE_BY_KEY.values():
        assert len(set(spec.value_keys)) == len(spec.value_keys) >= 2


def test_clean_attributes_accepts_valid_and_drops_empty_values():
    assert clean_attributes({"face_shape": "round", "glasses": "", "hair_style": None}) == {"face_shape": "round"}


@pytest.mark.parametrize("bad", [{"face_shape": "banana"}, {"nonsense": "x"}, {"glasses": 5}])
def test_clean_attributes_rejects_unknown_names_and_values(bad):
    with pytest.raises(AttributeValidationError):
        clean_attributes(bad)


def test_attribute_diff_lists_only_changes():
    diff = attribute_diff({"glasses": "none", "face_shape": "round"}, {"glasses": "glasses", "face_shape": "round"})
    assert [d["attribute"] for d in diff] == ["glasses"]


def test_meta_payload_matches_vocabulary():
    payload = meta_payload()
    assert [p["key"] for p in payload] == list(ATTRIBUTE_KEYS)
    assert all(p["values"] and p["label"] for p in payload)


def test_skin_colour_offers_white_brown_and_black_as_an_ordered_scale():
    spec = ATTRIBUTE_BY_KEY["skin_colour"]
    assert spec.label == "Skin colour" and spec.value_keys == ("white", "brown", "black")
    assert spec.ordered  # so "make the skin darker / lighter" can step along it
    assert [label for _, label in spec.values] == ["White / fair", "Brown / wheatish", "Black / dark"]
    assert VOCABULARY_VERSION == "1.1"  # the vocabulary changed, so its version moved


def test_every_ordered_attribute_has_a_step_baseline_that_is_one_of_its_values():
    for spec in ATTRIBUTES:
        if spec.ordered:
            assert STEP_BASELINES[spec.key] in spec.value_keys, spec.key


def test_skin_colour_values_are_validated_like_every_other_attribute():
    assert clean_attributes({"skin_colour": "brown"}) == {"skin_colour": "brown"}
    for bad in ("tan", "WHITE", "light", 3):
        with pytest.raises(AttributeValidationError):
            clean_attributes({"skin_colour": bad})


def test_colour_chips_are_valid_hex_for_every_value_and_reach_the_web_ui():
    spec = ATTRIBUTE_BY_KEY["skin_colour"]
    assert [v for v, _ in spec.swatches] == list(spec.value_keys)
    assert all(re.fullmatch(r"#[0-9A-Fa-f]{6}", chip) for _, chip in spec.swatches)
    payload = {p["key"]: p for p in meta_payload()}
    assert [v["swatch"] for v in payload["skin_colour"]["values"]] == [chip for _, chip in spec.swatches]
    assert all("swatch" not in v for key, p in payload.items() if key != "skin_colour" for v in p["values"])
