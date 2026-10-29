import pytest

from app.services.description_parser import get_parser
from app.services.description_parser.revision import interpret_revision

P = get_parser()
CURRENT = {"apparent_gender": "male", "age_description": "adult", "face_shape": "oval", "hair_length": "short",
           "eyebrows": "medium", "nose_shape": "narrow", "facial_hair": "beard", "glasses": "none"}  # fmt: skip


def plan(text, lang="en", current=None):
    return interpret_revision(P, text, CURRENT if current is None else current, lang)


def changes(p):
    return {c.attribute: (c.before, c.after) for c in p.changes}


def test_comparative_steps_along_an_ordered_scale():
    assert changes(plan("make the eyebrows thicker")) == {"eyebrows": ("medium", "thick")}
    assert changes(plan("make the eyebrows thinner")) == {"eyebrows": ("medium", "thin")}
    assert changes(plan("make the hair longer")) == {"hair_length": ("short", "medium")}


def test_comparative_targets_a_named_value():
    assert changes(plan("make the nose broader and the face rounder")) == {"nose_shape": ("narrow", "broad"), "face_shape": ("oval", "round")}


def test_step_from_an_unspecified_attribute_starts_at_a_stated_default():
    p = plan("make the eyebrows thicker", current={})
    assert changes(p) == {"eyebrows": (None, "thick")}
    assert "default" in p.changes[0].note


def test_scale_end_is_reported_not_exceeded():
    p = plan("make the eyebrows thicker", current={"eyebrows": "thick"})
    assert not p.changes and any("maximum" in n for n in p.notes)


def test_add_and_remove_in_one_instruction_keep_their_scopes_apart():
    assert changes(plan("add glasses and remove the beard")) == {"glasses": ("none", "glasses"), "facial_hair": ("beard", "none")}
    assert changes(plan("add a mustache and remove glasses", current={**CURRENT, "glasses": "glasses"})) == {
        "facial_hair": ("beard", "mustache"), "glasses": ("glasses", "none")}  # fmt: skip


def test_removal_verb_covers_a_whole_list():
    both = {**CURRENT, "glasses": "glasses"}
    assert changes(plan("remove the beard and glasses", current=both)) == {"facial_hair": ("beard", "none"), "glasses": ("glasses", "none")}


def test_pronouns_never_change_the_apparent_gender():
    p = plan("give her glasses")
    assert changes(p) == {"glasses": ("none", "glasses")}
    assert p.new_attributes["apparent_gender"] == "male"


def test_unsupported_instructions_are_listed_as_ignored_not_faked():
    p = plan("add a scar on the left cheek")  # scars are not in the vocabulary
    assert not p.changes and p.ignored and "scar" in p.ignored[0].text


def test_comparative_without_a_feature_is_explained():
    p = plan("make it thicker")
    assert not p.changes and "needs a feature" in p.ignored[0].reason


def test_removing_a_feature_the_sketch_does_not_have_is_a_noop_with_a_note():
    p = plan("remove the glasses")
    assert not p.changes and any("already" in n for n in p.notes)


def test_hindi_and_kannada_instructions():
    assert changes(plan("चश्मा जोड़ें", "hi")) == {"glasses": ("none", "glasses")}
    assert changes(plan("दाढ़ी हटाओ", "hi")) == {"facial_hair": ("beard", "none")}
    assert changes(plan("ಗಡ್ಡ ತೆಗೆಯಿರಿ", "kn")) == {"facial_hair": ("beard", "none")}
    assert changes(plan("ಕನ್ನಡಕ ಸೇರಿಸಿ", "kn")) == {"glasses": ("none", "glasses")}


def test_plan_summary_and_target_attribute():
    p = plan("make the eyebrows thicker and add glasses")
    assert p.target_attribute in {"eyebrows", "glasses"} and "Eyebrow" in p.summary


# ----------------------------------------------------------------------------- skin colour
def test_skin_colour_steps_darker_and_lighter_along_white_brown_black():
    assert changes(plan("make the skin darker", current={"skin_colour": "white"})) == {"skin_colour": ("white", "brown")}
    assert changes(plan("make the skin darker", current={"skin_colour": "brown"})) == {"skin_colour": ("brown", "black")}
    assert changes(plan("make the skin lighter", current={"skin_colour": "black"})) == {"skin_colour": ("black", "brown")}
    assert changes(plan("give him fairer skin", current={"skin_colour": "brown"})) == {"skin_colour": ("brown", "white")}


def test_skin_colour_scale_ends_are_reported_not_exceeded():
    p = plan("make the skin darker", current={"skin_colour": "black"})
    assert not p.changes and any("maximum" in n for n in p.notes)
    p = plan("make the skin lighter", current={"skin_colour": "white"})
    assert not p.changes and any("minimum" in n for n in p.notes)


def test_darker_from_an_unspecified_skin_colour_starts_at_a_stated_default():
    p = plan("make the skin darker", current={})
    assert changes(p) == {"skin_colour": (None, "brown")}
    assert "default" in p.changes[0].note and "White" in p.changes[0].note


@pytest.mark.parametrize("text,expected", [
    ("make the skin brown", "brown"),
    ("change the skin colour to black", "black"),
    ("make the skin white", "white"),
    ("make the face brown", "brown"),  # in an instruction the face may be coloured
])
def test_skin_colour_can_be_set_by_name(text, expected):
    assert changes(plan(text, current={"skin_colour": "white" if expected != "white" else "black"}))["skin_colour"][1] == expected


def test_make_the_face_darker_colours_the_skin():
    assert changes(plan("make the face darker", current={"skin_colour": "white"})) == {"skin_colour": ("white", "brown")}


def test_hair_colour_is_still_not_supported_and_says_so():
    for text in ("make the hair darker", "make the hair black"):
        p = plan(text, current={"skin_colour": "white"})
        assert not p.changes and p.ignored, text


def test_skin_colour_and_another_change_in_one_instruction():
    p = plan("make the skin brown and add glasses", current={"glasses": "none"})
    assert changes(p) == {"skin_colour": (None, "brown"), "glasses": ("none", "glasses")}


def test_skin_colour_instructions_in_hindi_and_kannada():
    assert changes(plan("त्वचा सांवली करो", "hi", current={"skin_colour": "white"})) == {"skin_colour": ("white", "brown")}
    assert changes(plan("चेहरा काला करो", "hi", current={"skin_colour": "white"})) == {"skin_colour": ("white", "black")}
    assert changes(plan("ಚರ್ಮ ಕಪ್ಪು ಮಾಡಿ", "kn", current={"skin_colour": "white"})) == {"skin_colour": ("white", "black")}
    assert changes(plan("ಮುಖ ಕಂದು ಮಾಡಿ", "kn", current={"skin_colour": "white"})) == {"skin_colour": ("white", "brown")}
