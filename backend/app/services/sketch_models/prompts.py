"""Turn structured attributes into English prompts for the AI engines.

Only attributes the investigator actually specified are mentioned. Unspecified features
are left out (not invented here) - but remember the AI model will still decide them.
All prompts describe a fictional face; no names or identifying information are ever added.
"""

from __future__ import annotations

from app.services.attributes import ATTRIBUTE_BY_KEY, Attributes

STYLE = (
    "Black-and-white graphite pencil forensic composite sketch, frontal head-and-shoulders portrait, "
    "neutral expression, plain white background, clean shading, no text, no watermark."
)
NEGATIVE = (
    "photograph, colour, text, caption, watermark, logo, multiple faces, extra people, distorted face, "
    "cartoon, anime, celebrity, side view"
)
# A black-and-white drawing cannot show a skin colour, so when the investigator chose one the sketch is asked for
# as a soft colour-pencil drawing instead (and "colour" is no longer a forbidden word).
STYLE_COLOUR = (
    "Soft colour-pencil forensic composite sketch, frontal head-and-shoulders portrait, "
    "neutral expression, plain white background, natural muted colours, clean shading, no text, no watermark."
)
NEGATIVE_COLOUR = (
    "photograph, text, caption, watermark, logo, multiple faces, extra people, distorted face, "
    "cartoon, anime, celebrity, side view"
)

AGE = {
    "young_adult": "young adult (about 18 to 29 years old)",
    "adult": "adult (about 30 to 44 years old)",
    "middle_aged": "middle-aged (about 45 to 59 years old)",
    "elderly": "elderly (over 60 years old)",
}
FACE = {
    "oval": "an oval face",
    "round": "a round face",
    "square": "a square face with a strong jaw",
    "long": "a long, oblong face",
    "heart": "a heart-shaped face with a narrow chin",
    "triangular": "a triangular face with a wide jaw and narrower forehead",
}
SKIN = {
    "white": "white (fair, light) skin",
    "brown": "brown (wheatish, medium) skin",
    "black": "black (dark) skin",
}
EYEBROWS = {"thin": "thin eyebrows", "medium": "medium-thickness eyebrows", "thick": "thick eyebrows"}
EYES = {"almond": "almond-shaped eyes", "round": "round eyes", "narrow": "narrow eyes", "droopy": "droopy eyes"}
NOSE = {
    "narrow": "a narrow nose", "broad": "a broad nose", "pointed": "a pointed nose",
    "flat": "a flat nose", "hooked": "a hooked nose", "upturned": "an upturned nose",
}  # fmt: skip
MOUTH = {
    "thin": "thin lips", "full": "full lips", "wide": "a wide mouth",
    "small": "a small mouth", "downturned": "a downturned mouth",
}  # fmt: skip
FACIAL_HAIR = {
    "none": "clean-shaven", "stubble": "light stubble", "mustache": "a mustache",
    "goatee": "a goatee", "beard": "a full beard",
}  # fmt: skip
HAIR_STYLE = {"straight": "straight", "wavy": "wavy", "curly": "curly"}


def describe_features(attributes: Attributes) -> list[str]:
    """English noun phrases for the specified attributes (used in both prompts and summaries)."""
    a = {k: v for k, v in attributes.items() if v}
    parts: list[str] = []
    if a.get("skin_colour"):
        parts.append(SKIN[a["skin_colour"]])
    if a.get("face_shape"):
        parts.append(FACE[a["face_shape"]])
    length, style = a.get("hair_length"), a.get("hair_style")
    if length == "bald":
        parts.append("a bald head")
    elif length or style:
        base = f"{length} hair" if length else "hair"
        if style in HAIR_STYLE:
            base = f"{length + ', ' if length else ''}{HAIR_STYLE[style]} hair"
        elif style == "receding":
            base += " with a receding hairline"
        elif style == "tied_back":
            base += " tied back"
        parts.append(base)
    for key, table in (("eyebrows", EYEBROWS), ("eye_shape", EYES), ("nose_shape", NOSE), ("mouth_shape", MOUTH)):
        if a.get(key):
            parts.append(table[a[key]])
    if a.get("facial_hair"):
        parts.append(FACIAL_HAIR[a["facial_hair"]])
    if a.get("glasses"):
        parts.append("wearing glasses" if a["glasses"] == "glasses" else "no glasses")
    return parts


def build_generation_prompt(attributes: Attributes, additional_details: str = "") -> tuple[str, str]:
    """Returns ``(prompt, negative_prompt)``."""
    a = {k: v for k, v in attributes.items() if v}
    who = "a fictional person"
    if a.get("age_description") or a.get("apparent_gender"):
        age = AGE.get(a.get("age_description", ""), "")
        gender = a.get("apparent_gender", "")
        who = "a fictional " + " ".join(x for x in (age, gender, "person" if not gender else "") if x).strip()
    features = describe_features(a)
    coloured = bool(a.get("skin_colour"))
    sentence = f"{STYLE_COLOUR if coloured else STYLE} Subject: {who}"
    if features:
        sentence += " with " + ", ".join(features)
    sentence += "."
    if additional_details.strip():
        sentence += f" Additional witness details: {additional_details.strip()}."
    return sentence, NEGATIVE_COLOUR if coloured else NEGATIVE


def english_change_summary(changes: list[tuple[str, str | None, str]]) -> str:
    """``[(attribute, before, after)]`` -> 'Eyebrows: thick. Glasses: add glasses.'"""
    phrases: list[str] = []
    for attribute, _before, after in changes:
        spec = ATTRIBUTE_BY_KEY[attribute]
        phrases.append(f"{spec.label}: {spec.label_for(after)}")
    return "; ".join(phrases)


def build_edit_prompt(instruction: str, change_summary_en: str, new_attributes: Attributes, additional_details: str = "") -> str:
    request = change_summary_en or instruction.strip()
    prompt = (
        f"Edit this forensic composite sketch. Requested change: {request}. "
        "Keep the same pencil-sketch style, pose, framing and plain background, and keep every feature "
        "that is not mentioned exactly as it is."
    )
    if "Skin colour" in change_summary_en:
        prompt += (
            " Apply the new skin colour to the whole face, ears and neck as soft colour-pencil colouring; "
            "the hair, eyes and clothes keep their own colours."
        )
    if change_summary_en and instruction.strip():
        prompt += f' (The investigator wrote: "{instruction.strip()}")'
    if additional_details.strip():
        prompt += f" Additional witness details: {additional_details.strip()}."
    return prompt
