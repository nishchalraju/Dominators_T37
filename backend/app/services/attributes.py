"""Controlled vocabulary for facial attributes.

This file is the single source of truth: the description parser, the attribute
editor in the web UI (via GET /api/meta/attributes), the schematic renderer, the
prompt builder and the custom-dataset validator all read the same values.

Attribute values are *estimates taken from a witness description*, not facts.
An attribute that is missing / ``None`` means "not specified" - we never guess.
"""

from __future__ import annotations

from dataclasses import dataclass

# Version of this vocabulary. Stored with datasets / evaluations so results can be
# compared fairly after the vocabulary changes.
#   1.0  the first 11 attributes
#   1.1  added ``skin_colour`` (white / brown / black)
VOCABULARY_VERSION = "1.1"


@dataclass(frozen=True)
class AttributeSpec:
    key: str
    label: str
    values: tuple[tuple[str, str], ...]  # (value, human readable label)
    ordered: bool = False  # True if the values form a scale (can step up / down)
    schematic_supported: bool = True  # can the rule-based renderer draw it?
    # Optional colour chips, ``(value, "#rrggbb")``. The web UI shows them next to the choices and the
    # schematic renderer paints exactly these colours, so what you pick is what is drawn.
    swatches: tuple[tuple[str, str], ...] = ()

    @property
    def value_keys(self) -> tuple[str, ...]:
        return tuple(v for v, _ in self.values)

    def label_for(self, value: str | None) -> str:
        if value is None:
            return "Not specified"
        return dict(self.values).get(value, value)

    def swatch_for(self, value: str | None) -> str | None:
        return dict(self.swatches).get(value) if value else None


ATTRIBUTES: tuple[AttributeSpec, ...] = (
    AttributeSpec(
        "apparent_gender",
        "Apparent gender",
        (("male", "Male"), ("female", "Female")),
    ),
    AttributeSpec(
        "age_description",
        "Apparent age",
        (
            ("young_adult", "Young adult (about 18-29)"),
            ("adult", "Adult (about 30-44)"),
            ("middle_aged", "Middle-aged (about 45-59)"),
            ("elderly", "Elderly (60+)"),
        ),
        ordered=True,
    ),
    AttributeSpec(
        "skin_colour",
        "Skin colour",
        # The three choices cover the common words witnesses use: fair / light = white, wheatish / dusky = brown,
        # dark = black. They are a coarse scale on purpose (a witness cannot give an exact shade).
        (("white", "White / fair"), ("brown", "Brown / wheatish"), ("black", "Black / dark")),
        ordered=True,  # white -> brown -> black, so "make the skin darker / lighter" can step along it
        swatches=(("white", "#F5D9C4"), ("brown", "#B9825A"), ("black", "#704C3A")),
    ),
    AttributeSpec(
        "face_shape",
        "Face shape",
        (
            ("oval", "Oval"),
            ("round", "Round"),
            ("square", "Square"),
            ("long", "Long / oblong"),
            ("heart", "Heart-shaped"),
            ("triangular", "Triangular (wide jaw)"),
        ),
    ),
    AttributeSpec(
        "hair_length",
        "Hair length",
        (("bald", "Bald"), ("short", "Short"), ("medium", "Medium"), ("long", "Long")),
        ordered=True,
    ),
    AttributeSpec(
        "hair_style",
        "Hair style",
        (
            ("straight", "Straight"),
            ("wavy", "Wavy"),
            ("curly", "Curly"),
            ("receding", "Receding hairline"),
            ("tied_back", "Tied back"),
        ),
    ),
    AttributeSpec(
        "eyebrows",
        "Eyebrow thickness",
        (("thin", "Thin"), ("medium", "Medium"), ("thick", "Thick")),
        ordered=True,
    ),
    AttributeSpec(
        "eye_shape",
        "Eye shape",
        (("almond", "Almond"), ("round", "Round"), ("narrow", "Narrow"), ("droopy", "Droopy")),
    ),
    AttributeSpec(
        "nose_shape",
        "Nose shape",
        (
            ("narrow", "Narrow"),
            ("broad", "Broad"),
            ("pointed", "Pointed"),
            ("flat", "Flat"),
            ("hooked", "Hooked"),
            ("upturned", "Upturned"),
        ),
    ),
    AttributeSpec(
        "mouth_shape",
        "Mouth shape",
        (
            ("thin", "Thin lips"),
            ("full", "Full lips"),
            ("wide", "Wide mouth"),
            ("small", "Small mouth"),
            ("downturned", "Downturned mouth"),
        ),
    ),
    AttributeSpec(
        "facial_hair",
        "Facial hair",
        (
            ("none", "None / clean-shaven"),
            ("stubble", "Stubble"),
            ("mustache", "Mustache"),
            ("goatee", "Goatee"),
            ("beard", "Beard"),
        ),
    ),
    AttributeSpec(
        "glasses",
        "Glasses",
        (("none", "No glasses"), ("glasses", "Wearing glasses")),
    ),
)

ATTRIBUTE_KEYS: tuple[str, ...] = tuple(a.key for a in ATTRIBUTES)
ATTRIBUTE_BY_KEY: dict[str, AttributeSpec] = {a.key: a for a in ATTRIBUTES}

# Where a "thicker / longer / older" step starts when the attribute was never specified.
# Only ordered attributes need a baseline. The sketch itself is drawn neutrally in that case.
# Skin colour starts at "white" because the neutral drawing is pale: "darker" then gives brown.
STEP_BASELINES: dict[str, str] = {"age_description": "adult", "hair_length": "short", "eyebrows": "medium", "skin_colour": "white"}

# Maximum length of the free-text "other features" field (only AI engines can use it).
MAX_ADDITIONAL_DETAILS = 300

Attributes = dict[str, str | None]


class AttributeValidationError(ValueError):
    """Raised when an attributes dictionary contains unknown keys or values."""


def clean_attributes(raw: dict | None, *, drop_empty: bool = True) -> Attributes:
    """Validate a ``{attribute: value}`` mapping against the controlled vocabulary.

    Empty strings and ``None`` mean "not specified". Unknown attribute names or
    values raise :class:`AttributeValidationError` (they are never silently kept).
    """
    cleaned: Attributes = {}
    for key, value in (raw or {}).items():
        spec = ATTRIBUTE_BY_KEY.get(key)
        if spec is None:
            raise AttributeValidationError(f"Unknown attribute '{key}'.")
        if value is None or (isinstance(value, str) and not value.strip()):
            if not drop_empty:
                cleaned[key] = None
            continue
        if not isinstance(value, str) or value not in spec.value_keys:
            allowed = ", ".join(spec.value_keys)
            raise AttributeValidationError(f"'{value}' is not a valid value for {spec.label} (allowed: {allowed}).")
        cleaned[key] = value
    return cleaned


def describe_attributes(attributes: Attributes) -> list[str]:
    """Human readable ``"Face shape: Oval"`` lines for the specified attributes."""
    lines: list[str] = []
    for spec in ATTRIBUTES:
        value = attributes.get(spec.key)
        if value:
            lines.append(f"{spec.label}: {spec.label_for(value)}")
    return lines


def attribute_diff(before: Attributes, after: Attributes) -> list[dict[str, str | None]]:
    """List the attributes whose value differs between two snapshots."""
    changes = []
    for spec in ATTRIBUTES:
        old, new = before.get(spec.key), after.get(spec.key)
        if old != new:
            changes.append({"attribute": spec.key, "label": spec.label, "before": old, "after": new})
    return changes


def meta_payload() -> list[dict]:
    """The vocabulary in the shape the frontend needs."""
    return [
        {
            "key": spec.key,
            "label": spec.label,
            "ordered": spec.ordered,
            "schematic_supported": spec.schematic_supported,
            "values": [
                {"value": v, "label": label, **({"swatch": spec.swatch_for(v)} if spec.swatches else {})}
                for v, label in spec.values
            ],
        }
        for spec in ATTRIBUTES
    ]


LANGUAGES: tuple[dict[str, str], ...] = (
    {"code": "en", "label": "English", "native_label": "English"},
    {"code": "kn", "label": "Kannada", "native_label": "ಕನ್ನಡ"},
    {"code": "hi", "label": "Hindi", "native_label": "हिन्दी"},
)
LANGUAGE_CODES: tuple[str, ...] = tuple(lang["code"] for lang in LANGUAGES)
LANGUAGE_LABELS: dict[str, str] = {lang["code"]: lang["label"] for lang in LANGUAGES}
