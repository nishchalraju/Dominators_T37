"""English lexicon.

How to read this file
---------------------
* NOUNS      - body-part words. They say which attributes an adjective can describe.
* BLOCKERS   - body-part / clothing words we do NOT model (chin, scar, hat ...).
               They stop an adjective from sticking to a faraway noun
               ("thick scar near the nose" must not make the nose thick).
* ADJECTIVES - words that only mean something next to a noun:
               {attribute: {value: (words...)}}
* STANDALONE - words that carry their own meaning: {phrase: ((attribute, value), ...)}
* A trailing ``*`` on a word means "any word that starts with this" (used for
  Hindi / Kannada inflections; English does not need it).

All entries are lower-case. This lexicon was written by the project developer
(``developer_authored``); it has not been reviewed by a second person.
"""

from __future__ import annotations

LANGUAGE = "en"
REVIEW_STATUS = "developer_authored"

NOUNS: dict[str, tuple[str, ...]] = {
    # face
    "face": ("face_shape",),
    "faced": ("face_shape",),
    "head": ("face_shape",),
    "face shape": ("face_shape",),
    "facial shape": ("face_shape",),
    # hair on the head
    "hair": ("hair_length", "hair_style"),
    "haired": ("hair_length", "hair_style"),
    "hairstyle": ("hair_length", "hair_style"),
    "hair style": ("hair_length", "hair_style"),
    "haircut": ("hair_length", "hair_style"),
    "hair cut": ("hair_length", "hair_style"),
    "hairdo": ("hair_length", "hair_style"),
    "hairline": ("hair_style",),
    # skin colour: only these words own it. "face" does not, so "black face mask" is never read as a skin colour
    "skin": ("skin_colour",),
    "skinned": ("skin_colour",),
    "complexion": ("skin_colour",),
    "complexioned": ("skin_colour",),
    "skin tone": ("skin_colour",),
    "skin colour": ("skin_colour",),
    "skin color": ("skin_colour",),
    "skin colored": ("skin_colour",),
    "skin coloured": ("skin_colour",),
    "skin shade": ("skin_colour",),
    # eyebrows, eyes, nose, mouth
    "eyebrows": ("eyebrows",),
    "eyebrow": ("eyebrows",),
    "eye brows": ("eyebrows",),
    "eye brow": ("eyebrows",),
    "brows": ("eyebrows",),
    "brow": ("eyebrows",),
    "eyes": ("eye_shape",),
    "eye": ("eye_shape",),
    "eyed": ("eye_shape",),
    "nose": ("nose_shape",),
    "mouth": ("mouth_shape",),
    "lips": ("mouth_shape",),
    "lip": ("mouth_shape",),
    # person words - "old man", "young woman"
    "man": ("age_description",),
    "woman": ("age_description",),
    "male": ("age_description",),
    "female": ("age_description",),
    "person": ("age_description",),
    "guy": ("age_description",),
    "lady": ("age_description",),
    "gentleman": ("age_description",),
    "individual": ("age_description",),
    "fellow": ("age_description",),
}

BLOCKERS: tuple[str, ...] = (
    "chin", "forehead", "cheek", "cheeks", "cheekbone", "cheekbones", "ear", "ears", "earlobes",
    "neck", "jaw", "jawline", "teeth", "scar", "scars", "mole", "moles",
    "tattoo", "tattoos", "build", "body", "height", "voice", "eyelashes", "lashes", "shoulders",
    "temples", "expression", "dimples", "dimple", "wrinkles", "freckles", "birthmark", "pimples",
    "acne", "earring", "earrings", "hat", "cap", "turban", "scarf", "helmet", "mask", "clothes",
    "shirt", "jacket", "hoodie", "tshirt", "bindi",
)  # fmt: skip

ADJECTIVES: dict[str, dict[str, tuple[str, ...]]] = {
    "face_shape": {
        "round": ("round", "circular", "rounded"),
        "square": ("square", "squared", "boxy"),
        "long": ("long", "elongated"),
    },
    "hair_length": {
        "short": ("short", "cropped", "trimmed"),
        "medium": ("medium", "medium length", "mid length", "average length"),
        "long": ("long", "lengthy"),
    },
    "hair_style": {
        "straight": ("straight", "sleek"),
    },
    "eyebrows": {
        "thick": ("thick", "bushy", "heavy", "dense", "bold", "full", "prominent"),
        "thin": ("thin", "sparse", "faint", "slender", "fine"),
        "medium": ("medium", "average", "normal", "moderate", "regular"),
    },
    "eye_shape": {
        "round": ("round", "circular", "rounded"),
        "narrow": ("narrow", "slit", "squinty"),
        "droopy": ("droopy", "drooping", "sleepy", "hooded", "downturned"),
    },
    "nose_shape": {
        "narrow": ("narrow", "thin", "slim", "slender", "pinched"),
        "broad": ("broad", "wide", "flared", "bulbous"),
        "pointed": ("pointed", "pointy", "sharp"),
        "flat": ("flat", "flattened"),
        "hooked": ("hooked", "aquiline", "beaked", "roman"),
        "upturned": ("upturned", "turned up", "snub", "button", "pug"),
    },
    "mouth_shape": {
        "thin": ("thin", "tight", "pursed"),
        "full": ("full", "plump", "pouty", "fleshy", "thick"),
        "wide": ("wide", "broad", "large", "big"),
        "small": ("small", "tiny", "little"),
        "downturned": ("downturned", "frowning", "drooping", "turned down", "sad"),
    },
    "age_description": {
        "elderly": ("old", "aged"),
        "young_adult": ("young", "youthful"),
    },
    # Only next to "skin", "complexion", "skinned" ... ("dark skin", "skin is brown", "fair-skinned").
    # "light" is deliberately NOT here ("light stubble"): "light skin" is spelled out in STANDALONE.
    "skin_colour": {
        "white": ("white", "fair", "pale", "pallid"),
        "brown": (
            "brown", "light brown", "dark brown", "medium brown", "tan", "tanned", "olive", "bronze", "bronzed",
        ),
        "black": ("black", "dark", "ebony"),
    },
}

_MALE = (("apparent_gender", "male"),)
_FEMALE = (("apparent_gender", "female"),)

STANDALONE: dict[str, tuple[tuple[str, str], ...]] = {
    # face shape (unambiguous words)
    "oval": (("face_shape", "oval"),),
    "egg shaped": (("face_shape", "oval"),),
    "elliptical": (("face_shape", "oval"),),
    "oblong": (("face_shape", "long"),),
    "heart shaped": (("face_shape", "heart"),),
    "triangular": (("face_shape", "triangular"),),
    "pear shaped": (("face_shape", "triangular"),),
    # hair length / style
    "bald": (("hair_length", "bald"),),
    "shaved head": (("hair_length", "bald"),),
    "shaven head": (("hair_length", "bald"),),
    "no hair": (("hair_length", "bald"),),
    "buzz cut": (("hair_length", "short"),),
    "crew cut": (("hair_length", "short"),),
    "close cropped": (("hair_length", "short"),),
    "closely cropped": (("hair_length", "short"),),
    "shoulder length": (("hair_length", "medium"),),
    "waist length": (("hair_length", "long"),),
    "wavy": (("hair_style", "wavy"),),
    "curly": (("hair_style", "curly"),),
    "curls": (("hair_style", "curly"),),
    "frizzy": (("hair_style", "curly"),),
    "ponytail": (("hair_style", "tied_back"),),
    "pony tail": (("hair_style", "tied_back"),),
    "bun": (("hair_style", "tied_back"),),
    "tied back": (("hair_style", "tied_back"),),
    "pulled back": (("hair_style", "tied_back"),),
    "receding": (("hair_style", "receding"),),
    "receding hairline": (("hair_style", "receding"),),
    "balding": (("hair_style", "receding"),),
    # eye shape
    "almond": (("eye_shape", "almond"),),
    "almond shaped": (("eye_shape", "almond"),),
    # facial hair
    "clean shaven": (("facial_hair", "none"),),
    "clean shave": (("facial_hair", "none"),),
    "smooth shaven": (("facial_hair", "none"),),
    "beardless": (("facial_hair", "none"),),
    "no facial hair": (("facial_hair", "none"),),
    "stubble": (("facial_hair", "stubble"),),
    "stubbly": (("facial_hair", "stubble"),),
    "unshaven": (("facial_hair", "stubble"),),
    "designer stubble": (("facial_hair", "stubble"),),
    "five oclock shadow": (("facial_hair", "stubble"),),
    "mustache": (("facial_hair", "mustache"),),
    "moustache": (("facial_hair", "mustache"),),
    "mustached": (("facial_hair", "mustache"),),
    "moustached": (("facial_hair", "mustache"),),
    "handlebar": (("facial_hair", "mustache"),),
    "goatee": (("facial_hair", "goatee"),),
    "soul patch": (("facial_hair", "goatee"),),
    "beard": (("facial_hair", "beard"),),
    "bearded": (("facial_hair", "beard"),),
    "full beard": (("facial_hair", "beard"),),
    "long beard": (("facial_hair", "beard"),),
    "short beard": (("facial_hair", "beard"),),
    "thick beard": (("facial_hair", "beard"),),
    "trimmed beard": (("facial_hair", "beard"),),
    # glasses
    "glasses": (("glasses", "glasses"),),
    "eyeglasses": (("glasses", "glasses"),),
    "spectacles": (("glasses", "glasses"),),
    "specs": (("glasses", "glasses"),),
    "bespectacled": (("glasses", "glasses"),),
    # apparent gender
    "male": _MALE,
    "man": _MALE,
    "gentleman": _MALE,
    "guy": _MALE,
    "female": _FEMALE,
    "woman": _FEMALE,
    "lady": _FEMALE,
    # apparent age
    "elderly": (("age_description", "elderly"),),
    "senior": (("age_description", "elderly"),),
    "middle aged": (("age_description", "middle_aged"),),
    "young adult": (("age_description", "young_adult"),),
    "adult": (("age_description", "adult"),),
}

# Skin colour words that mean a complexion on their own, without the word "skin" ...
STANDALONE.update({
    "wheatish": (("skin_colour", "brown"),),
    "dusky": (("skin_colour", "brown"),),
    "swarthy": (("skin_colour", "brown"),),
})
# ... "light skin" / "medium complexion" (spelled out because "light" and "medium" also describe hair) ...
for _word, _value in (("light", "white"), ("medium", "brown")):
    for _skin in ("skin", "skinned", "complexion", "complexioned"):
        STANDALONE[f"{_word} {_skin}"] = (("skin_colour", _value),)
# ... and "a white man", "a black woman": the colour word directly in front of a person word. The person word also
# stays a noun, so "an old white man" still reads the age. "a man in white" is NOT a skin colour (clothes).
for _colour in ("white", "black", "brown"):
    for _person, _who in (
        ("man", _MALE), ("male", _MALE), ("guy", _MALE), ("gentleman", _MALE),
        ("woman", _FEMALE), ("female", _FEMALE), ("lady", _FEMALE),
    ):
        STANDALONE[f"{_colour} {_person}"] = (("skin_colour", _colour), *_who)
        NOUNS[f"{_colour} {_person}"] = ("age_description",)

# Pronouns give a weaker hint about apparent gender. They are used when reading a
# witness description, but ignored when interpreting a revision instruction
# ("give her glasses" must not change the sketch's gender).
PRONOUNS: dict[str, tuple[tuple[str, str], ...]] = {
    "he": _MALE, "his": _MALE, "him": _MALE, "himself": _MALE,
    "she": _FEMALE, "her": _FEMALE, "hers": _FEMALE, "herself": _FEMALE,
}  # fmt: skip

# A negator "reverses" a facial-hair / glasses match that follows (or precedes) it.
NEGATORS_BEFORE: tuple[str, ...] = (
    "no", "not", "without", "never", "nor", "neither", "lacks", "lacking",
    "dont", "doesnt", "didnt", "isnt", "wasnt", "arent", "werent", "hasnt", "havent",
)  # fmt: skip
NEGATORS_AFTER: tuple[str, ...] = ()

# Used only when interpreting an *instruction* ("remove the glasses").
REMOVAL_VERBS: tuple[str, ...] = (
    "remove", "removed", "removing", "delete", "erase", "shave", "shaved", "eliminate", "drop", "off",
)  # fmt: skip

# Words that end a clause when we report unrecognised phrases.
CONJUNCTIONS: tuple[str, ...] = (
    "and", "with", "but", "also", "plus", "while", "who", "which", "has", "have", "having", "had",
    "wearing", "wears", "wore", "sporting", "then", "or", "although", "though",
)  # fmt: skip

# Function words that never count as "unrecognised content".
STOPWORDS: tuple[str, ...] = (
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "of", "in", "on", "at", "to",
    "for", "as", "by", "from", "that", "this", "these", "those", "it", "its", "very", "quite", "rather",
    "slightly", "somewhat", "fairly", "really", "pretty", "about", "around", "approximately", "roughly",
    "looks", "look", "looking", "looked", "seems", "seemed", "appears", "appeared", "seen", "saw", "said",
    "think", "thought", "believe", "i", "me", "my", "there", "they", "their", "them", "some", "any",
    "kind", "sort", "type", "like", "got", "features", "feature", "appearance", "his", "her", "he", "she",
    "him", "no", "not", "without", "never", "nor", "neither", "dont", "doesnt", "didnt", "isnt", "wasnt",
    "also", "maybe", "perhaps", "probably", "seemingly", "almost", "nearly", "over", "under", "above",
    "please", "make", "making", "give", "show",
    "want", "wanted", "need", "would", "should", "could", "can", "will", "let", "us", "so", "too", "more",
    "less", "much", "bit", "little", "lot", "up", "down", "into", "one", "ones", "other", "another",
    "just", "only", "still", "even", "all", "both", "each", "every", "same", "such", "than", "then",
    "person", "individual", "people", "someone", "somebody", "fellow", "subject", "suspect", "figure",
)  # fmt: skip

STOP_PREFIXES: tuple[str, ...] = ()
PREFIX_EXCEPTIONS: tuple[str, ...] = ()

# --- age expressions -------------------------------------------------------
AGE_UNIT_WORDS: tuple[str, ...] = ("year", "years", "yr", "yrs", "yo", "yearold", "yearsold")
AGE_CONTEXT_WORDS: tuple[str, ...] = ("aged", "age", "ages")
AGE_CONNECTORS: tuple[str, ...] = ()
DECADE_MODIFIERS: dict[str, int] = {"early": 2, "mid": 5, "middle": 5, "late": 8}  # added to the decade
DECADE_WORDS: dict[str, int] = {
    "twenties": 20, "thirties": 30, "forties": 40, "fifties": 50,
    "sixties": 60, "seventies": 70, "eighties": 80, "nineties": 90,
}  # fmt: skip
TENS_WORDS: dict[str, int] = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}  # fmt: skip
ONES_WORDS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
}  # fmt: skip

# --- comparatives used by the revision interpreter (English instructions only) ----
# "make the eyebrows thicker": a step along an ORDERED scale  -> {attribute: +1 / -1}
COMPARATIVE_STEPS: dict[str, dict[str, int]] = {
    "longer": {"hair_length": +1},
    "shorter": {"hair_length": -1},
    "thicker": {"eyebrows": +1},
    "bushier": {"eyebrows": +1},
    "heavier": {"eyebrows": +1},
    "thinner": {"eyebrows": -1},
    "sparser": {"eyebrows": -1},
    "older": {"age_description": +1},
    "younger": {"age_description": -1},
    "darker": {"skin_colour": +1},
    "lighter": {"skin_colour": -1},
    "paler": {"skin_colour": -1},
    "fairer": {"skin_colour": -1},
}
# "make the nose broader": a jump to a NAMED value of an unordered attribute -> {attribute: value}
COMPARATIVE_TARGETS: dict[str, dict[str, str]] = {
    "broader": {"nose_shape": "broad"},
    "wider": {"nose_shape": "broad", "mouth_shape": "wide"},
    "bigger": {"mouth_shape": "wide"},
    "larger": {"mouth_shape": "wide"},
    "narrower": {"nose_shape": "narrow", "eye_shape": "narrow"},
    "thinner": {"nose_shape": "narrow", "mouth_shape": "thin"},
    "slimmer": {"nose_shape": "narrow"},
    "tighter": {"mouth_shape": "thin"},
    "fuller": {"mouth_shape": "full"},
    "thicker": {"mouth_shape": "full"},
    "plumper": {"mouth_shape": "full"},
    "smaller": {"mouth_shape": "small"},
    "rounder": {"face_shape": "round", "eye_shape": "round"},
    "squarer": {"face_shape": "square"},
    "longer": {"face_shape": "long"},
    "flatter": {"nose_shape": "flat"},
    "sharper": {"nose_shape": "pointed"},
    "pointier": {"nose_shape": "pointed"},
    "curlier": {"hair_style": "curly"},
    "wavier": {"hair_style": "wavy"},
    "straighter": {"hair_style": "straight"},
    "browner": {"skin_colour": "brown"},
}

CONTRAST: tuple[str, ...] = ("but", "however", "although", "though", "except", "yet")

# --- revision instructions ---------------------------------------------------------------
# Action verbs: ignored (not reported as "unrecognised") when reading an instruction, and they
# end the scope of a removal verb ("remove the beard AND add glasses").
INSTRUCTION_WORDS: tuple[str, ...] = (
    "add", "put", "give", "make", "change", "set", "turn", "update", "adjust", "modify", "replace",
    "apply", "include", "insert", "draw", "use", "now", "instead", "off",
)  # fmt: skip
# Does the verb come AFTER the thing it acts on? (English: "remove the beard"; Hindi / Kannada: "दाढ़ी हटाओ")
VERB_FINAL = False

# Word endings that make any verb negative (Kannada: ಧರಿಸುವುದಿಲ್ಲ, ಇರಲಿಲ್ಲ ...). Empty for languages that use a separate word.
NEGATOR_SUFFIXES: tuple[str, ...] = ()
