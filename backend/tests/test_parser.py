"""The multilingual description parser. All text below is synthetic."""

import pytest

from app.services.description_parser import PARSER_VERSION, get_parser
from app.services.description_parser.normalize import tokenize

P = get_parser()

EN = "A man about 35 years old with a round face, thick eyebrows, a narrow nose and short curly hair. He has a beard and wears glasses."
HI = "वह आदमी लगभग 35 साल का था। उसका चेहरा गोल, भौंहें मोटी, नाक पतली और छोटे घुंघराले बाल थे। दाढ़ी थी और चश्मा पहना था।"
KN = "ಅವನಿಗೆ ಸುಮಾರು ೩೫ ವರ್ಷ ವಯಸ್ಸು. ದುಂಡನೆಯ ಮುಖ, ದಪ್ಪ ಹುಬ್ಬುಗಳು, ತೆಳುವಾದ ಮೂಗು, ಚಿಕ್ಕ ಗುಂಗುರು ಕೂದಲು. ಗಡ್ಡ ಇದೆ ಮತ್ತು ಕನ್ನಡಕ ಧರಿಸಿದ್ದಾನೆ."
EXPECTED = {
    "apparent_gender": "male", "age_description": "adult", "face_shape": "round", "hair_length": "short",
    "hair_style": "curly", "eyebrows": "thick", "nose_shape": "narrow", "facial_hair": "beard", "glasses": "glasses",
}  # fmt: skip


def got(text, lang):
    return P.parse(text, lang).extracted


def test_same_face_gives_same_canonical_values_in_all_three_languages():
    assert got(EN, "en") == got(HI, "hi") == got(KN, "kn") == EXPECTED


def test_every_value_carries_the_words_that_caused_it():
    result = P.parse(EN, "en")
    for detail in result.details:
        assert detail.evidence and detail.evidence in EN or "|" in detail.evidence
    assert next(d for d in result.details if d.attribute == "eyebrows").evidence == "thick eyebrows"


def test_unrecognised_phrases_are_reported_not_guessed():
    result = P.parse("A man with a scar on his left cheek and a tattoo.", "en")
    texts = " ".join(u.text for u in result.unrecognized)
    assert "scar" in texts and "tattoo" in texts
    assert result.extracted == {"apparent_gender": "male"}


def test_nothing_recognised_leaves_everything_empty_with_a_warning():
    result = P.parse("The weather was windy.", "en")
    assert result.extracted == {}
    assert any("No supported" in w for w in result.warnings)


def test_there_is_no_confidence_score_anywhere():
    result = P.parse(EN, "en")
    assert not hasattr(result, "confidence")
    assert all(not hasattr(d, "confidence") for d in result.details)


@pytest.mark.parametrize(
    "text,lang,attr,value",
    [
        ("He had no glasses.", "en", "glasses", "none"),
        ("He is not wearing glasses", "en", "glasses", "none"),
        ("clean shaven man", "en", "facial_hair", "none"),
        ("बिना चश्मा", "hi", "glasses", "none"),
        ("दाढ़ी नहीं थी", "hi", "facial_hair", "none"),
        ("ಕನ್ನಡಕ ಇರಲಿಲ್ಲ", "kn", "glasses", "none"),
        ("ಕನ್ನಡಕ ಧರಿಸುವುದಿಲ್ಲ", "kn", "glasses", "none"),  # regression: negative verb ending
    ],
)
def test_negation_in_every_language(text, lang, attr, value):
    assert got(text, lang)[attr] == value


def test_mustache_but_no_beard_is_a_mustache():
    assert got("He has a mustache but no beard.", "en")["facial_hair"] == "mustache"


def test_single_negated_feature_does_not_invent_a_value():
    result = P.parse("He has no mustache.", "en")
    assert "facial_hair" not in result.extracted
    assert any("mustache" in u.text for u in result.unrecognized)


def test_conflicting_values_are_left_empty_and_reported():
    result = P.parse("The man has a round face and an oval face.", "en")
    assert "face_shape" not in result.extracted
    assert result.conflicts and result.conflicts[0].attribute == "face_shape"
    assert set(result.conflicts[0].values) == {"round", "oval"}


@pytest.mark.parametrize(
    "text,lang,bucket",
    [
        ("He is 25 years old", "en", "young_adult"),
        ("aged 35", "en", "adult"),
        ("in her late forties", "en", "middle_aged"),
        ("a 62-year-old man", "en", "elderly"),
        ("35-40 years old", "en", "adult"),
        ("३५ वर्ष", "hi", "adult"),
        ("तीस साल का आदमी", "hi", "adult"),
        ("ಸುಮಾರು ೫೫ ವರ್ಷ", "kn", "middle_aged"),
    ],
)
def test_age_expressions_are_bucketed(text, lang, bucket):
    assert got(text, lang)["age_description"] == bucket


def test_old_inside_an_age_expression_is_not_read_as_the_adjective_old():
    # regression: "35 years old" + "man" used to give a clash between adult and elderly
    assert got("A man about 35 years old with a round face.", "en")["age_description"] == "adult"
    assert got("A 22-year-old woman.", "en")["age_description"] == "young_adult"


def test_bare_numbers_are_not_ages():
    assert "age_description" not in got("He weighs 70 kg and is 180 cm tall.", "en")


def test_ages_under_18_are_not_supported_and_are_reported():
    result = P.parse("a 12 year old", "en")
    assert "age_description" not in result.extracted
    assert any("under 18" in u.reason for u in result.unrecognized)


def test_adjectives_bind_to_the_nearest_matching_noun_only():
    assert got("thick eyebrows and a narrow nose", "en") == {"eyebrows": "thick", "nose_shape": "narrow"}
    # "thin" next to a body part we do not model must not attach to a faraway nose
    assert "nose_shape" not in got("a thin scar near the nose", "en")


def test_hindi_predicate_adjectives_stay_in_their_own_clause():
    assert got("चेहरा गोल, भौंहें मोटी, नाक पतली", "hi") == {"face_shape": "round", "eyebrows": "thick", "nose_shape": "narrow"}


def test_indic_words_are_not_split_at_vowel_signs():
    tokens = [t.raw for t in tokenize("अंडाकार चेहरा ಅಂಡಾಕಾರದ ಮುಖ")]
    assert tokens == ["अंडाकार", "चेहरा", "ಅಂಡಾಕಾರದ", "ಮುಖ"]


def test_kannada_false_friends_do_not_match():
    assert got("ಮುಖ್ಯ ಸಾಕ್ಷಿ ಇಲ್ಲಿ ಇದ್ದರು", "kn") == {}  # "main witness was here" - no face / negation


def test_language_mismatch_and_code_mixing_are_flagged():
    r = P.parse("दाढ़ी और चश्मा", "en")
    assert any("looks like Hindi" in w for w in r.warnings)
    assert r.extracted == {"facial_hair": "beard", "glasses": "glasses"}
    mixed = P.parse("round face और beard", "en")
    assert mixed.extracted["face_shape"] == "round" and mixed.extracted["facial_hair"] == "beard"


def test_unreviewed_word_lists_are_declared_and_warned_about():
    r = P.parse(HI, "hi")
    assert r.lexicon_status == {"en": "developer_authored", "hi": "unreviewed", "kn": "unreviewed"}
    assert any("unreviewed draft" in w for w in r.warnings)
    assert not any("unreviewed" in w for w in P.parse(EN, "en").warnings)


def test_pronoun_only_gender_is_labelled_as_weak_evidence():
    detail = next(d for d in P.parse("He has a beard.", "en").details if d.attribute == "apparent_gender")
    assert detail.match_type == "pronoun" and "pronoun" in (detail.note or "")


def test_parser_reports_its_version():
    assert P.parse(EN, "en").parser_version == PARSER_VERSION


def test_parsing_is_deterministic():
    assert P.parse(KN, "kn").attributes == P.parse(KN, "kn").attributes


# ----------------------------------------------------------------------------- skin colour
@pytest.mark.parametrize(
    "text,lang,expected",
    [
        ("A man with fair skin and a round face.", "en", "white"),
        ("pale complexion", "en", "white"),
        ("He is fair-skinned.", "en", "white"),
        ("light skin", "en", "white"),
        ("white skin", "en", "white"),
        ("brown skin, oval face", "en", "brown"),
        ("a wheatish complexion", "en", "brown"),
        ("dusky", "en", "brown"),
        ("olive skinned woman", "en", "brown"),
        ("dark brown skin", "en", "brown"),
        ("medium complexion", "en", "brown"),
        ("dark skin and thick eyebrows", "en", "black"),
        ("a dark-skinned man", "en", "black"),
        ("black skin", "en", "black"),
        ("very dark complexion", "en", "black"),
        ("His skin was brown.", "en", "brown"),
        ("skin colour is black", "en", "black"),
        ("a white man with a beard", "en", "white"),
        ("an old black woman", "en", "black"),
        ("उसका रंग गोरा था", "hi", "white"),
        ("गोरी महिला", "hi", "white"),
        ("सफेद त्वचा", "hi", "white"),
        ("वह आदमी सांवला था", "hi", "brown"),
        ("गेहुँआ रंग", "hi", "brown"),
        ("भूरी त्वचा", "hi", "brown"),
        ("काली त्वचा", "hi", "black"),
        ("उसका रंग काला था", "hi", "black"),
        ("उसकी त्वचा का रंग काला है", "hi", "black"),
        ("ಬಿಳಿ ಚರ್ಮ", "kn", "white"),
        ("ಬೆಳ್ಳಗಿನ ಮೈಬಣ್ಣ", "kn", "white"),
        ("ಅವಳು ಬೆಳ್ಳಗಿದ್ದಳು", "kn", "white"),
        ("ಕಂದು ಬಣ್ಣದ ಚರ್ಮ", "kn", "brown"),
        ("ಗೋಧಿ ಬಣ್ಣ", "kn", "brown"),
        ("ಕಪ್ಪು ಚರ್ಮ", "kn", "black"),
        ("ಅವನ ಮೈಬಣ್ಣ ಕಪ್ಪು", "kn", "black"),
        ("ಅವನು ಕಪ್ಪಗಿದ್ದ", "kn", "black"),
    ],
)
def test_skin_colour_is_read_from_english_hindi_and_kannada(text, lang, expected):
    assert got(text, lang).get("skin_colour") == expected


def test_the_same_face_gives_the_same_skin_colour_in_all_three_languages():
    en = "A man about 45 years old with dark skin and a round face."
    hi = "लगभग 45 साल का आदमी, काली त्वचा और गोल चेहरा।"
    kn = "ಸುಮಾರು ೪೫ ವರ್ಷದ ಗಂಡಸು, ಕಪ್ಪು ಚರ್ಮ ಮತ್ತು ದುಂಡನೆಯ ಮುಖ."
    assert got(en, "en") == got(hi, "hi") == got(kn, "kn")
    assert got(en, "en")["skin_colour"] == "black"


@pytest.mark.parametrize(
    "text,lang",
    [
        ("black hair and brown eyes", "en"),
        ("a man with white hair and a white beard", "en"),
        ("dark hair, a round face", "en"),
        ("wearing a black face mask and a white shirt", "en"),
        ("A man in black with a round face", "en"),
        ("light stubble and thick eyebrows", "en"),
        ("tall, dark and handsome", "en"),
        ("a black jacket", "en"),
        ("बाल काले थे", "hi"),
        ("बालों का रंग काला था और उसने काले रंग की जैकेट पहनी थी।", "hi"),
        ("सफेद बाल और सफेद दाढ़ी", "hi"),
        ("भूरे बाल", "hi"),
        ("ಕಂದು ಬಣ್ಣದ ಕೂದಲು ಮತ್ತು ಬಿಳಿ ಗಡ್ಡ", "kn"),
        ("ಬೆಳ್ಳಿ ಬಣ್ಣದ ಕನ್ನಡಕ", "kn"),
        ("ಕಪ್ಪು ಕೂದಲು", "kn"),
    ],
)
def test_colours_of_hair_clothes_and_masks_are_never_read_as_a_skin_colour(text, lang):
    assert "skin_colour" not in got(text, lang)


def test_a_colour_word_next_to_hair_is_reported_as_not_converted():
    result = P.parse("black hair and fair skin", "en")
    assert result.extracted == {"skin_colour": "white"}
    assert any("black hair" in u.text for u in result.unrecognized)  # hair colour is not in the vocabulary


def test_conflicting_skin_colours_are_left_empty_and_reported():
    result = P.parse("pale skin, but dark skin around the eyes", "en")
    assert "skin_colour" not in result.extracted
    assert any(c.attribute == "skin_colour" and set(c.values) == {"white", "black"} for c in result.conflicts)


def test_skin_colour_evidence_is_the_words_that_caused_it():
    detail = next(d for d in P.parse("A man with dark skin.", "en").details if d.attribute == "skin_colour")
    assert detail.value == "black" and detail.evidence == "dark skin"


def test_the_parser_version_moved_when_the_word_lists_changed():
    assert PARSER_VERSION == "1.2.0"
