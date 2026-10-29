"""Kannada lexicon.

Kannada is agglutinative: the noun ಮುಖ ("face") becomes ಮುಖದ, ಮುಖವು, ಮುಖಕ್ಕೆ ...
so most entries are *stems* ending in ``*`` ("any word that starts with this").
Stems can over-match, so ``PREFIX_EXCEPTIONS`` lists known false friends.

IMPORTANT: written by the project developer and NOT reviewed by a native speaker.
The review status below is shown in the UI and stored with every parse. Do not
change it to "reviewed" unless a qualified reviewer has actually checked the file.
"""

from __future__ import annotations

LANGUAGE = "kn"
REVIEW_STATUS = "unreviewed"

NOUNS: dict[str, tuple[str, ...]] = {
    "ಮುಖ*": ("face_shape",),
    "ಮೋರೆ*": ("face_shape",),
    "ಚಹರೆ*": ("face_shape",),
    "ತಲೆ*": ("face_shape",),
    "ಕೂದಲ*": ("hair_length", "hair_style"),
    "ತಲೆಕೂದಲ*": ("hair_length", "hair_style"),
    "ತಲೆಗೂದಲ*": ("hair_length", "hair_style"),
    "ಕೇಶ*": ("hair_length", "hair_style"),
    "ಹೇರ್*": ("hair_length", "hair_style"),
    "ಹುಬ್ಬ*": ("eyebrows",),
    "ಕಣ್ಣ*": ("eye_shape",),
    "ಮೂಗ*": ("nose_shape",),
    "ಬಾಯಿ*": ("mouth_shape",),
    "ತುಟಿ*": ("mouth_shape",),
    # skin colour. Only these own it: the bare word ಬಣ್ಣ (colour) stays a blocker (hair colour, clothes colour).
    "ಮೈಬಣ್ಣ*": ("skin_colour",),
    "ಮೈ ಬಣ್ಣ*": ("skin_colour",),
    "ಚರ್ಮ*": ("skin_colour",),
    "ಚರ್ಮ* ಬಣ್ಣ*": ("skin_colour",),
    "ಬಣ್ಣ* ಚರ್ಮ*": ("skin_colour",),
    "ಮುಖ* ಬಣ್ಣ*": ("skin_colour",),
    # person words
    "ವ್ಯಕ್ತಿ*": ("age_description",),
    "ಮನುಷ್ಯ*": ("age_description",),
    "ಪುರುಷ*": ("age_description",),
    "ಮಹಿಳೆ*": ("age_description",),
    "ಹೆಂಗಸ*": ("age_description",),
    "ಗಂಡಸ*": ("age_description",),
}

BLOCKERS: tuple[str, ...] = (
    "ಗದ್ದ*", "ಹಣೆ*", "ಕೆನ್ನೆ*", "ಕಿವಿ*", "ಕುತ್ತಿಗೆ*", "ಬಣ್ಣ*", "ದವಡೆ*", "ಹಲ್ಲ*", "ಗಾಯ*",
    "ಕಲೆ*", "ಮಚ್ಚೆ*", "ಹಚ್ಚೆ*", "ಎತ್ತರ*", "ಧ್ವನಿ*", "ರೆಪ್ಪೆ*", "ಭುಜ*", "ಪೇಟ*", "ಟೋಪಿ*", "ಬಟ್ಟೆ*",
    "ಅಂಗಿ*", "ಸುಕ್ಕು*", "ಗುರುತು*",
)  # fmt: skip

ADJECTIVES: dict[str, dict[str, tuple[str, ...]]] = {
    "face_shape": {
        "round": ("ದುಂಡ*", "ಗುಂಡ*", "ವೃತ್ತಾಕಾರ*"),
        "square": ("ಚೌಕ*", "ಚೌಕಾಕಾರ*"),
        "long": ("ಉದ್ದ*",),
    },
    "hair_length": {
        "short": ("ಚಿಕ್ಕ*", "ಸಣ್ಣ*", "ಗಿಡ್ಡ*"),
        "medium": ("ಮಧ್ಯಮ ಉದ್ದ*", "ಮಧ್ಯಮ*"),
        "long": ("ಉದ್ದ*",),
    },
    "hair_style": {
        "straight": ("ನೇರ*",),
    },
    "eyebrows": {
        "thick": ("ದಪ್ಪ*", "ದಟ್ಟ*"),
        "thin": ("ತೆಳು*", "ತೆಳ್ಳ*"),
        "medium": ("ಮಧ್ಯಮ*", "ಸಾಧಾರಣ*"),
    },
    "eye_shape": {
        "round": ("ದುಂಡ*", "ಗುಂಡ*"),
        "narrow": ("ಕಿರಿದ*",),
        "droopy": ("ಜೋಲ*", "ಇಳಿಬಿದ್ದ*"),
    },
    "nose_shape": {
        "narrow": ("ತೆಳು*", "ಕಿರಿದ*", "ಸಪೂರ*"),
        "broad": ("ಅಗಲ*", "ದಪ್ಪ*"),
        "pointed": ("ಚೂಪ*", "ಮೊನಚ*"),
        "flat": ("ಚಪ್ಪಟೆ*",),
        "hooked": ("ಗಿಣಿ*", "ಬಾಗಿದ*"),
        "upturned": ("ಮೇಲ್ಮುಖ*", "ಮೇಲಕ್ಕೆ ಬಾಗಿದ*"),
    },
    # Only next to a skin word ("ಕಪ್ಪು ಚರ್ಮ", "ಮೈಬಣ್ಣ ಬಿಳಿ"); ಕಂದು ಬಣ್ಣದ ಕೂದಲು (brown hair) is not a skin colour.
    "skin_colour": {
        "white": ("ಬಿಳಿ*", "ಬೆಳ್ಳ*", "ಬಿಳುಪ*"),
        "brown": ("ಕಂದು*", "ಗೋಧಿ*"),
        "black": ("ಕಪ್ಪ*",),
    },
    "mouth_shape": {
        "thin": ("ತೆಳು*", "ತೆಳ್ಳ*"),
        "full": ("ದಪ್ಪ*", "ತುಂಬಿದ*"),
        "wide": ("ಅಗಲ*", "ದೊಡ್ಡ*"),
        "small": ("ಚಿಕ್ಕ*", "ಸಣ್ಣ*"),
        "downturned": ("ಕೆಳಮುಖ*", "ಕೆಳಗೆ ಬಾಗಿದ*", "ಜೋಲ*"),
    },
}

_MALE = (("apparent_gender", "male"),)
_FEMALE = (("apparent_gender", "female"),)

STANDALONE: dict[str, tuple[tuple[str, str], ...]] = {
    # face shape
    "ಅಂಡಾಕಾರ*": (("face_shape", "oval"),),
    "ಮೊಟ್ಟೆಯಾಕಾರ*": (("face_shape", "oval"),),
    "ಹೃದಯಾಕಾರ*": (("face_shape", "heart"),),
    "ತ್ರಿಕೋನ*": (("face_shape", "triangular"),),
    # hair
    "ಬೋಳು*": (("hair_length", "bald"),),
    "ಬಕ್ಕ*": (("hair_length", "bald"),),
    "ಅಲೆಯಾದ*": (("hair_style", "wavy"),),
    "ಅಲೆಅಲೆ*": (("hair_style", "wavy"),),
    "ಅಲೆಯಂತಹ*": (("hair_style", "wavy"),),
    "ಗುಂಗುರ*": (("hair_style", "curly"),),
    "ಕರ್ಲಿ*": (("hair_style", "curly"),),
    "ಜಡೆ*": (("hair_style", "tied_back"),),
    "ತುರುಬ*": (("hair_style", "tied_back"),),
    "ಪೋನಿಟೇಲ್*": (("hair_style", "tied_back"),),
    "ಹಿಂದೆ ಕಟ್ಟ*": (("hair_style", "tied_back"),),
    # eyes
    "ಬಾದಾಮಿ*": (("eye_shape", "almond"),),
    # facial hair
    "ಕ್ಲೀನ್ ಶೇವ್*": (("facial_hair", "none"),),
    "ಕ್ಲೀನ್ಶೇವ್*": (("facial_hair", "none"),),
    "ಗಡ್ಡವಿಲ್ಲ*": (("facial_hair", "!beard"),),
    "ಗಡ್ಡವಿರಲಿಲ್ಲ*": (("facial_hair", "!beard"),),
    "ಮೀಸೆಯಿಲ್ಲ*": (("facial_hair", "!mustache"),),
    "ಮೀಸೆಯಿರಲಿಲ್ಲ*": (("facial_hair", "!mustache"),),
    "ಕುರುಚಲು ಗಡ್ಡ*": (("facial_hair", "stubble"),),
    "ಸ್ಟಬಲ್*": (("facial_hair", "stubble"),),
    "ಮೀಸೆ*": (("facial_hair", "mustache"),),
    "ಮೇಕೆ ಗಡ್ಡ*": (("facial_hair", "goatee"),),
    "ಮೇಕೆಗಡ್ಡ*": (("facial_hair", "goatee"),),
    "ಗಡ್ಡ*": (("facial_hair", "beard"),),
    "ದಾಡಿ*": (("facial_hair", "beard"),),
    # glasses
    "ಕನ್ನಡಕ*": (("glasses", "glasses"),),
    "ಚಷ್ಮಾ*": (("glasses", "glasses"),),
    # apparent gender / age words
    "ಪುರುಷ*": _MALE,
    "ಗಂಡಸ*": _MALE,
    "ಮಹಿಳೆ*": _FEMALE,
    "ಹೆಂಗಸ*": _FEMALE,
    "ಹೆಣ್ಣು*": _FEMALE,
    "ಸ್ತ್ರೀ*": _FEMALE,
    "ಯುವಕ*": (("apparent_gender", "male"), ("age_description", "young_adult")),
    "ಯುವತಿ*": (("apparent_gender", "female"), ("age_description", "young_adult")),
    "ಯುವ*": (("age_description", "young_adult"),),
    "ವಯಸ್ಕ*": (("age_description", "adult"),),
    "ಮಧ್ಯವಯಸ್ಕ*": (("age_description", "middle_aged"),),
    "ಮಧ್ಯ ವಯಸ್ಸ*": (("age_description", "middle_aged"),),
    "ವೃದ್ಧ*": (("age_description", "elderly"),),
    "ವೃದ್ಧೆ*": (("apparent_gender", "female"), ("age_description", "elderly")),
    "ಮುದುಕ*": (("apparent_gender", "male"), ("age_description", "elderly")),
    "ಮುದುಕಿ*": (("apparent_gender", "female"), ("age_description", "elderly")),
    "ವಯಸ್ಸಾದ*": (("age_description", "elderly"),),
    "ಹಿರಿಯ*": (("age_description", "elderly"),),
}

# "he is fair / dark" - the verb forms that describe the person (not the adjective forms used for hair etc.)
STANDALONE.update({
    "ಗೋಧಿ ಬಣ್ಣ*": (("skin_colour", "brown"),),  # "wheat colour" is how a wheatish complexion is described
    "ಬೆಳ್ಳಗಿದ್ದ*": (("skin_colour", "white"),),
    "ಬೆಳ್ಳಗಿರುವ*": (("skin_colour", "white"),),
    "ಬೆಳ್ಳಗೆ*": (("skin_colour", "white"),),
    "ಕಪ್ಪಗಿದ್ದ*": (("skin_colour", "black"),),
    "ಕಪ್ಪಗಿರುವ*": (("skin_colour", "black"),),
    "ಕಪ್ಪಗೆ*": (("skin_colour", "black"),),
})

PRONOUNS: dict[str, tuple[tuple[str, str], ...]] = {
    "ಅವನು": _MALE,
    "ಅವನ*": _MALE,
    "ಅವಳು": _FEMALE,
    "ಅವಳ*": _FEMALE,
}

# Kannada puts the negator after the noun: "ಗಡ್ಡ ಇಲ್ಲ" (beard not-there).
NEGATORS_BEFORE: tuple[str, ...] = ()
NEGATORS_AFTER: tuple[str, ...] = (
    "ಇಲ್ಲ*", "ಇರಲಿಲ್ಲ*", "ಇರುವುದಿಲ್ಲ*", "ಹೊಂದಿಲ್ಲ*", "ಹೊಂದಿರಲಿಲ್ಲ*", "ಧರಿಸಿಲ್ಲ*", "ಧರಿಸಿರಲಿಲ್ಲ*",
    "ರಹಿತ*", "ಅಲ್ಲ*",
)  # fmt: skip

REMOVAL_VERBS: tuple[str, ...] = ("ತೆಗೆ*", "ತೆಗೆಯ*", "ಅಳಿಸ*", "ಶೇವ್*")

CONTRAST: tuple[str, ...] = ("ಆದರೆ", "ಆದರು")

CONJUNCTIONS: tuple[str, ...] = (
    "ಮತ್ತು", "ಹಾಗೂ", "ಹಾಗು", "ಆದರೆ", "ಜೊತೆಗೆ", "ಜೊತೆ", "ಅಥವಾ", "ಇಲ್ಲವೇ", "ಇಲ್ಲವೆ", "ಮತ್ತೆ", "ಆದರು",
)  # fmt: skip

STOPWORDS: tuple[str, ...] = (
    "ಒಂದು", "ಆ", "ಈ", "ಇದೆ", "ಇತ್ತು", "ತುಂಬಾ", "ಬಹಳ", "ಸ್ವಲ್ಪ", "ಕೂಡ", "ಸಹ", "ಅವರ", "ಅದು", "ಇದು",
    "ಎಂದು", "ಅದರ", "ಇದರ", "ಆಗಿದೆ", "ಅಥವಾ", "ಮತ್ತು", "ಹಾಗೂ", "ಹಾಗು", "ಜೊತೆಗೆ", "ಜೊತೆ", "ಸುಮಾರು",
    "ಅಂದಾಜು", "ಮಾತ್ರ", "ಕೂಡಾ", "ಇನ್ನೂ", "ಇನ್ನು", "ಅಲ್ಲಿ", "ಇಲ್ಲಿ", "ಎಂಬ", "ಎಂದರೆ", "ಅವರು",
    "ಅವರಿಗೆ", "ತನ್ನ", "ನಾನು", "ನನ್ನ", "ನೀವು", "ದಯವಿಟ್ಟು", "ಬೇಕು", "ಮಾಡಿ", "ಮಾಡು", "ಹೆಚ್ಚು", "ಕಡಿಮೆ",
)  # fmt: skip

STOP_PREFIXES: tuple[str, ...] = (
    "ಇದ್ದ", "ಇರುವ", "ಇರುತ್ತ", "ಇರ್ತ", "ಹೊಂದಿ", "ಕಾಣ", "ಆಗಿ", "ಮಾಡ", "ಇಲ್ಲ", "ಅಲ್ಲ", "ವರ್ಷ", "ವಯಸ್ಸ",
    "ಸುಮಾರ", "ಅಂದಾಜ", "ಧರಿಸ", "ಇರಲಿಲ್ಲ", "ಕೊಡ", "ತೋರ", "ವ್ಯಕ್ತಿ", "ಮನುಷ್ಯ",
)  # fmt: skip

# Stems that must NOT match even though they start with a lexicon stem.
PREFIX_EXCEPTIONS: tuple[str, ...] = (
    "ಮುಖ್ಯ",  # "main / chief" starts with the "face" stem
    "ಕನ್ನಡಕ್ಕ",  # "to Kannada" starts with the "glasses" stem
    "ಇಲ್ಲವೆ",  # "or" starts with the "not-there" stem
    "ಇಲ್ಲವೇ",
    "ಅಲೆಮಾರಿ",  # "nomad"
    "ಇಲ್ಲಿ",  # "here" starts with the "not-there" stem
    "ಅಲ್ಲಿ",  # "there"
    "ಬೆಳ್ಳಿ",  # "silver" starts with the "fair" stem ಬೆಳ್ಳ
)

# --- age expressions -------------------------------------------------------
AGE_UNIT_WORDS: tuple[str, ...] = ("ವರ್ಷ*", "ವಯಸ್ಸ*", "ವಯಸ್ಸು*", "ಹರೆಯ*")
AGE_CONNECTORS: tuple[str, ...] = ()
AGE_CONTEXT_WORDS: tuple[str, ...] = ("ವಯಸ್ಸು*", "ವಯಸ್ಸ*")
DECADE_MODIFIERS: dict[str, int] = {}
DECADE_WORDS: dict[str, int] = {}
TENS_WORDS: dict[str, int] = {
    "ಇಪ್ಪತ್ತ*": 20, "ಮೂವತ್ತ*": 30, "ನಲವತ್ತ*": 40, "ಐವತ್ತ*": 50, "ಅರವತ್ತ*": 60, "ಎಪ್ಪತ್ತ*": 70, "ಎಂಬತ್ತ*": 80,
}  # fmt: skip
ONES_WORDS: dict[str, int] = {}

COMPARATIVE_STEPS: dict[str, dict[str, int]] = {}
COMPARATIVE_TARGETS: dict[str, dict[str, str]] = {}

INSTRUCTION_WORDS: tuple[str, ...] = ("ಸೇರಿಸ*", "ಹಾಕ*", "ಮಾಡ*", "ಬದಲಾಯಿಸ*", "ಬದಲಿಸ*", "ಕೊಡ*", "ಇಡ*")
VERB_FINAL = True

# Word endings that make any verb negative (Kannada: ಧರಿಸುವುದಿಲ್ಲ, ಇರಲಿಲ್ಲ ...). Empty for languages that use a separate word.
NEGATOR_SUFFIXES: tuple[str, ...] = ("ದಿಲ್ಲ", "ಲಿಲ್ಲ")
