"""Hindi (Devanagari) lexicon.

Same structure as ``lexicon_en.py``. Hindi adjectives change with gender and
number (लंबा / लंबी / लंबे) so each form is listed.

IMPORTANT: written by the project developer and NOT reviewed by a native speaker.
The review status below is shown in the UI and stored with every parse. Do not
change it to "reviewed" unless a qualified reviewer has actually checked the file.
"""

from __future__ import annotations

LANGUAGE = "hi"
REVIEW_STATUS = "unreviewed"

NOUNS: dict[str, tuple[str, ...]] = {
    "चेहरा": ("face_shape",),
    "चेहरे": ("face_shape",),
    "चेहरों": ("face_shape",),
    "शक्ल": ("face_shape",),
    "सिर": ("face_shape",),
    "बाल": ("hair_length", "hair_style"),
    "बालों": ("hair_length", "hair_style"),
    "केश": ("hair_length", "hair_style"),
    "हेयरस्टाइल": ("hair_length", "hair_style"),
    "हेयरकट": ("hair_length", "hair_style"),
    "भौंह": ("eyebrows",),
    "भौंहें": ("eyebrows",),
    "भौंहों": ("eyebrows",),
    "भौहें": ("eyebrows",),
    "भौहों": ("eyebrows",),
    "भौं": ("eyebrows",),
    "भवें": ("eyebrows",),
    "आँख": ("eye_shape",),
    "आंख": ("eye_shape",),
    "आँखें": ("eye_shape",),
    "आंखें": ("eye_shape",),
    "आँखे": ("eye_shape",),
    "आंखे": ("eye_shape",),
    "आँखों": ("eye_shape",),
    "आंखों": ("eye_shape",),
    "नेत्र": ("eye_shape",),
    "नाक": ("nose_shape",),
    "नासिका": ("nose_shape",),
    "मुँह": ("mouth_shape",),
    "मुंह": ("mouth_shape",),
    "होंठ": ("mouth_shape",),
    "होंठों": ("mouth_shape",),
    "होठ": ("mouth_shape",),
    "होठों": ("mouth_shape",),
    "ओंठ": ("mouth_shape",),
    "ओंठों": ("mouth_shape",),
    # skin colour. Only these own it: the bare word "रंग" (colour) stays a blocker because it is also
    # बालों का रंग (hair colour) and कुर्ते का रंग (clothes colour).
    "त्वचा": ("skin_colour",),
    "चमड़ी": ("skin_colour",),
    "चमडी": ("skin_colour",),
    "रंगत": ("skin_colour",),
    "त्वचा का रंग": ("skin_colour",),
    "त्वचा के रंग": ("skin_colour",),
    "चमड़ी का रंग": ("skin_colour",),
    "चेहरे का रंग": ("skin_colour",),
    "चेहरे की रंगत": ("skin_colour",),
    # person words (for "बूढ़ा आदमी" style phrases)
    "आदमी": ("age_description",),
    "पुरुष": ("age_description",),
    "महिला": ("age_description",),
    "औरत": ("age_description",),
    "स्त्री": ("age_description",),
    "व्यक्ति": ("age_description",),
    "इंसान": ("age_description",),
    "शख्स": ("age_description",),
}

BLOCKERS: tuple[str, ...] = (
    "ठुड्डी", "माथा", "माथे", "गाल", "गालों", "कान", "कानों", "गर्दन", "रंग", "जबड़ा",
    "जबड़े", "दांत", "दाँत", "निशान", "तिल", "घाव", "कद", "आवाज़", "आवाज", "पलकें", "कंधे",
    "पगड़ी", "टोपी", "कपड़े", "कमीज़", "कमीज", "कुर्ता", "टैटू", "झुर्रियां", "झुर्रियाँ",
)  # fmt: skip

ADJECTIVES: dict[str, dict[str, tuple[str, ...]]] = {
    "face_shape": {
        "round": ("गोल", "गोलाकार", "गोलमटोल"),
        "square": ("चौकोर", "चौकोना", "चौकोन", "चौकोनी", "चौकोने"),
        "long": ("लंबा", "लंबी", "लंबे", "लम्बा", "लम्बी", "लम्बे", "लंबोतरा", "लंबोतरी", "लंबोतरे"),
    },
    "hair_length": {
        "short": ("छोटा", "छोटी", "छोटे"),
        "medium": ("मध्यम", "मझोला", "मझोली", "मझोले"),
        "long": ("लंबा", "लंबी", "लंबे", "लम्बा", "लम्बी", "लम्बे", "बड़ा", "बड़ी", "बड़े"),
    },
    "hair_style": {
        "straight": ("सीधा", "सीधी", "सीधे"),
    },
    "eyebrows": {
        "thick": ("मोटी", "मोटे", "मोटा", "घनी", "घने", "घना", "झाड़ीदार", "झाडीदार", "भारी"),
        "thin": ("पतली", "पतले", "पतला", "हल्की", "हल्के", "बारीक"),
        "medium": ("मध्यम", "सामान्य", "औसत"),
    },
    "eye_shape": {
        "round": ("गोल", "गोलाकार"),
        "narrow": ("संकरी", "संकरे", "संकरा", "पतली", "पतले", "पतला"),
        "droopy": ("झुकी", "झुके", "झुका", "ढलकी", "ढलके", "लटकी", "लटके", "उनींदी", "उनींदे"),
    },
    "nose_shape": {
        "narrow": ("पतली", "पतला", "पतले", "संकरी", "संकरा", "संकरे", "बारीक"),
        "broad": ("चौड़ी", "चौड़ा", "चौड़े", "चौडी", "चौडा", "चौडे", "मोटी", "मोटा", "मोटे", "फैली", "फैला", "फैले"),
        "pointed": ("नुकीली", "नुकीला", "नुकीले", "तीखी", "तीखा", "तीखे", "नोकदार"),
        "flat": ("चपटी", "चपटा", "चपटे", "धंसी", "धंसा"),
        "upturned": ("उठी हुई", "उठा हुआ", "उठे हुए", "ऊपर उठी", "ऊपर की ओर"),
    },
    # Only next to a skin word ("काली त्वचा", "त्वचा का रंग काला"). गोरा / साँवला have their own entries in STANDALONE.
    "skin_colour": {
        "white": ("सफेद", "सफ़ेद", "उजला", "उजली", "उजले"),
        "brown": ("भूरा", "भूरी", "भूरे"),
        "black": ("काला", "काली", "काले"),
    },
    "mouth_shape": {
        "thin": ("पतले", "पतली", "पतला"),
        "full": ("मोटे", "मोटी", "मोटा", "भरे", "भरी", "भरा", "भरे हुए"),
        "wide": ("चौड़ा", "चौड़ी", "चौड़े", "चौडा", "चौडी", "चौडे", "बड़ा", "बड़ी", "बड़े"),
        "small": ("छोटा", "छोटी", "छोटे"),
        "downturned": ("नीचे की ओर", "झुके", "झुकी", "लटके", "लटकी", "उतरे"),
    },
}

_MALE = (("apparent_gender", "male"),)
_FEMALE = (("apparent_gender", "female"),)

STANDALONE: dict[str, tuple[tuple[str, str], ...]] = {
    # face shape
    "अंडाकार": (("face_shape", "oval"),),
    "अंडे जैसा": (("face_shape", "oval"),),
    "अंडे जैसी": (("face_shape", "oval"),),
    "अंडे जैसे": (("face_shape", "oval"),),
    "दिल के आकार": (("face_shape", "heart"),),
    "दिल जैसा": (("face_shape", "heart"),),
    "हृदयाकार": (("face_shape", "heart"),),
    "त्रिकोण": (("face_shape", "triangular"),),
    "त्रिकोणीय": (("face_shape", "triangular"),),
    "तिकोना": (("face_shape", "triangular"),),
    "तिकोनी": (("face_shape", "triangular"),),
    "तिकोने": (("face_shape", "triangular"),),
    "त्रिकोणी": (("face_shape", "triangular"),),
    # hair
    "गंजा": (("hair_length", "bald"),),
    "गंजी": (("hair_length", "bald"),),
    "गंजे": (("hair_length", "bald"),),
    "मुंडा सिर": (("hair_length", "bald"),),
    "सिर मुंडा": (("hair_length", "bald"),),
    "सफाचट सिर": (("hair_length", "bald"),),
    "क्रू कट": (("hair_length", "short"),),
    "कंधे तक": (("hair_length", "medium"),),
    "कमर तक": (("hair_length", "long"),),
    "लहरदार": (("hair_style", "wavy"),),
    "लहरीले": (("hair_style", "wavy"),),
    "लहरियादार": (("hair_style", "wavy"),),
    "घुंघराले": (("hair_style", "curly"),),
    "घुँघराले": (("hair_style", "curly"),),
    "घुंघराला": (("hair_style", "curly"),),
    "घुँघराला": (("hair_style", "curly"),),
    "घुंघराली": (("hair_style", "curly"),),
    "घुँघराली": (("hair_style", "curly"),),
    "छल्लेदार": (("hair_style", "curly"),),
    "पोनीटेल": (("hair_style", "tied_back"),),
    "जूड़ा": (("hair_style", "tied_back"),),
    "जूडा": (("hair_style", "tied_back"),),
    "बंधे हुए": (("hair_style", "tied_back"),),
    "पीछे बंधे": (("hair_style", "tied_back"),),
    "पीछे बाँधे": (("hair_style", "tied_back"),),
    "पीछे बांधे": (("hair_style", "tied_back"),),
    "हेयरलाइन पीछे": (("hair_style", "receding"),),
    "पीछे हटती हेयरलाइन": (("hair_style", "receding"),),
    "पीछे हटते बाल": (("hair_style", "receding"),),
    # eyes
    "बादाम जैसी": (("eye_shape", "almond"),),
    "बादाम जैसे": (("eye_shape", "almond"),),
    "बादाम जैसा": (("eye_shape", "almond"),),
    "बादाम सी": (("eye_shape", "almond"),),
    "बादाम के आकार": (("eye_shape", "almond"),),
    # nose
    "तोते जैसी": (("nose_shape", "hooked"),),
    "तोते जैसा": (("nose_shape", "hooked"),),
    "बाज़ जैसी": (("nose_shape", "hooked"),),
    "बाज जैसी": (("nose_shape", "hooked"),),
    "तोते की चोंच जैसी": (("nose_shape", "hooked"),),
    # facial hair
    "क्लीन शेव": (("facial_hair", "none"),),
    "क्लीनशेव": (("facial_hair", "none"),),
    "सफाचट चेहरा": (("facial_hair", "none"),),
    "हल्की दाढ़ी": (("facial_hair", "stubble"),),
    "हल्की दाढी": (("facial_hair", "stubble"),),
    "खूंटी": (("facial_hair", "stubble"),),
    "खूँटी": (("facial_hair", "stubble"),),
    "मूँछ": (("facial_hair", "mustache"),),
    "मूंछ": (("facial_hair", "mustache"),),
    "मूछ": (("facial_hair", "mustache"),),
    "मूँछें": (("facial_hair", "mustache"),),
    "मूंछें": (("facial_hair", "mustache"),),
    "मूछें": (("facial_hair", "mustache"),),
    "मूँछों": (("facial_hair", "mustache"),),
    "मूंछों": (("facial_hair", "mustache"),),
    "बकरी दाढ़ी": (("facial_hair", "goatee"),),
    "बकरी दाढी": (("facial_hair", "goatee"),),
    "दाढ़ी": (("facial_hair", "beard"),),
    "दाढी": (("facial_hair", "beard"),),
    # glasses
    "चश्मा": (("glasses", "glasses"),),
    "चश्मे": (("glasses", "glasses"),),
    "चश्मों": (("glasses", "glasses"),),
    "ऐनक": (("glasses", "glasses"),),
    "चश्माधारी": (("glasses", "glasses"),),
    # apparent gender / age words
    "पुरुष": _MALE,
    "आदमी": _MALE,
    "मर्द": _MALE,
    "सज्जन": _MALE,
    "महिला": _FEMALE,
    "औरत": _FEMALE,
    "स्त्री": _FEMALE,
    "युवक": (("apparent_gender", "male"), ("age_description", "young_adult")),
    "युवती": (("apparent_gender", "female"), ("age_description", "young_adult")),
    "वृद्धा": (("apparent_gender", "female"), ("age_description", "elderly")),
    "बुढ़िया": (("apparent_gender", "female"), ("age_description", "elderly")),
    "युवा": (("age_description", "young_adult"),),
    "जवान": (("age_description", "young_adult"),),
    "नौजवान": (("age_description", "young_adult"),),
    "वयस्क": (("age_description", "adult"),),
    "अधेड़": (("age_description", "middle_aged"),),
    "प्रौढ़": (("age_description", "middle_aged"),),
    "मध्यम आयु": (("age_description", "middle_aged"),),
    "मध्यम उम्र": (("age_description", "middle_aged"),),
    "बुजुर्ग": (("age_description", "elderly"),),
    "बुज़ुर्ग": (("age_description", "elderly"),),
    "बूढ़ा": (("age_description", "elderly"),),
    "बूढ़ी": (("age_description", "elderly"),),
    "बूढ़े": (("age_description", "elderly"),),
    "वृद्ध": (("age_description", "elderly"),),
    "उम्रदराज़": (("age_description", "elderly"),),
    "उम्रदराज": (("age_description", "elderly"),),
}

# Complexion words that mean the skin on their own. "रंग" next to them is understood together with them
# (otherwise "उसका रंग गोरा था" would report "रंग" as an unrecognised word).
_FAIR = ("गोरा", "गोरी", "गोरे")
_WHEATISH_OR_DUSKY = (
    "साँवला", "सांवला", "साँवली", "सांवली", "साँवले", "सांवले",
    "गेहुँआ", "गेहुंआ", "गेहूँआ", "गेहूंआ", "गेहुएँ", "गेहुएं",
)  # fmt: skip
for _value, _words in (("white", _FAIR), ("brown", _WHEATISH_OR_DUSKY)):
    for _word in _words:
        STANDALONE[_word] = (("skin_colour", _value),)
        for _noun in ("रंग", "रंगत"):
            STANDALONE[f"{_noun} {_word}"] = (("skin_colour", _value),)
            STANDALONE[f"{_word} {_noun}"] = (("skin_colour", _value),)
# "काला" is also black hair / black clothes, so a bare "रंग काला" is NOT enough ("बालों का रंग काला"). It counts
# when the colour belongs to the person: "उसका रंग काला था", "आदमी का रंग काला".
for _owner in ("उसका", "इसका", "आदमी का", "पुरुष का", "महिला का", "औरत का", "व्यक्ति का", "युवक का", "युवती का"):
    for _word in ("काला", "काले"):
        STANDALONE[f"{_owner} रंग {_word}"] = (("skin_colour", "black"),)

PRONOUNS: dict[str, tuple[tuple[str, str], ...]] = {}

# Hindi puts the negator after the noun ("दाढ़ी नहीं"), except बिना / बगैर ("बिना दाढ़ी").
NEGATORS_BEFORE: tuple[str, ...] = ("बिना", "बग़ैर", "बगैर")
NEGATORS_AFTER: tuple[str, ...] = ("नहीं", "नही", "रहित", "विहीन")

REMOVAL_VERBS: tuple[str, ...] = ("हटा*", "निकाल*", "मिटा*", "शेव")

CONJUNCTIONS: tuple[str, ...] = (
    "और", "तथा", "व", "एवं", "लेकिन", "मगर", "परंतु", "पर", "साथ", "जिसके", "जिसकी", "जिसका",
    "या", "जबकि", "फिर",
)  # fmt: skip

STOPWORDS: tuple[str, ...] = (
    "है", "हैं", "था", "थी", "थे", "थीं", "हो", "होता", "होती", "होते", "का", "की", "के", "को", "में",
    "से", "पर", "एक", "वह", "वो", "उसके", "उसकी", "उसका", "उसे", "उनके", "उनकी", "यह", "ये", "इस",
    "उस", "जो", "बहुत", "काफी", "काफ़ी", "थोड़ा", "थोड़ी", "थोड़े", "ही", "भी", "वाला", "वाली", "वाले",
    "जैसा", "जैसी", "जैसे", "सा", "सी", "तक", "ओर", "लगता", "लगती", "लगते", "दिखता", "दिखती",
    "दिखते", "दिखाई", "देता", "देती", "देते", "रहा", "रही", "रहे", "कुछ", "करें", "करो", "कीजिए",
    "कर", "दो", "दें", "देना", "चाहिए", "इसे", "उन्हें", "अपने", "मेरे", "मैंने", "मुझे", "हुए", "हुआ",
    "हुई", "कि", "तो", "नहीं", "नही", "बिना", "बगैर", "बग़ैर", "रहित", "विहीन", "उम्र", "आयु", "साल",
    "वर्ष", "बरस", "लगभग", "करीब", "क़रीब", "आसपास", "कोई", "इसकी", "इसका", "इसके", "मेरा", "मेरी",
    "हमें", "आप", "बनाएं", "बनाओ", "बनाइए", "बना", "जरा", "ज़रा", "अधिक", "ज्यादा", "ज़्यादा", "कम",
    "थोड़ा", "ऊपर", "नीचे", "सबसे", "बस", "सिर्फ़", "सिर्फ", "केवल", "अब", "वहाँ", "वहां", "यहाँ", "यहां",
)  # fmt: skip

# word beginnings that are never facial content (verbs like पहना/पहने/पहनी "wore", दिखता "looks", ...)
STOP_PREFIXES: tuple[str, ...] = ("पहन", "दिख", "लग", "बन", "व्यक्ति", "इंसान", "शख्स")
PREFIX_EXCEPTIONS: tuple[str, ...] = ()

# --- age expressions -------------------------------------------------------
AGE_UNIT_WORDS: tuple[str, ...] = ("साल", "वर्ष", "बरस", "वर्षीय", "आसपास")
AGE_CONNECTORS: tuple[str, ...] = ("के",)
AGE_CONTEXT_WORDS: tuple[str, ...] = ("उम्र", "आयु")
DECADE_MODIFIERS: dict[str, int] = {}
DECADE_WORDS: dict[str, int] = {}
TENS_WORDS: dict[str, int] = {
    "बीस": 20, "तीस": 30, "चालीस": 40, "पचास": 50, "साठ": 60, "सत्तर": 70, "अस्सी": 80,
}  # fmt: skip
ONES_WORDS: dict[str, int] = {}

COMPARATIVE_STEPS: dict[str, dict[str, int]] = {}
COMPARATIVE_TARGETS: dict[str, dict[str, str]] = {}

CONTRAST: tuple[str, ...] = ("लेकिन", "मगर", "परंतु", "किंतु")

INSTRUCTION_WORDS: tuple[str, ...] = (
    "जोड़*", "जोडे*", "जोड़ो", "लगा*", "बना*", "कर*", "डाल*", "बदल*", "दीजिए", "दीजिये", "दें", "दो", "रख*",
)  # fmt: skip
VERB_FINAL = True

# Word endings that make any verb negative (Kannada: ಧರಿಸುವುದಿಲ್ಲ, ಇರಲಿಲ್ಲ ...). Empty for languages that use a separate word.
NEGATOR_SUFFIXES: tuple[str, ...] = ()
