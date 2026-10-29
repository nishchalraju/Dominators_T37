"""Responsible-use wording. One place, so the UI, the API and the PDF always say the same thing."""

from __future__ import annotations

PRELIMINARY = "Preliminary investigative aid - requires human review."
NO_IDENTIFICATION = (
    "This system does not identify people. It performs no face recognition, no face matching and no search of "
    "photo databases, and its output must never be treated as evidence of identity."
)

RESPONSIBLE_USE: list[str] = [
    "SketchAssist AI is a preliminary investigative aid. Every sketch and every extracted attribute needs human review.",
    "It does not identify anyone: there is no face recognition, no matching against photos and no suspect search.",
    "Attributes are editable estimates taken from a witness's words. Phrases the system does not understand are listed, not guessed.",
    "AI-generated images can contain invented details and social biases. They are labelled as AI-generated everywhere.",
    "Names are personal data. A case records the investigator's name and the witness's name so the report can show them: enter only "
    "what your organisation's rules allow (a code such as W-01 is fine for a witness who must stay anonymous), and never enter "
    "personal details about a suspect.",
    "A sketch is not a photograph. Do not publish or circulate one without authorisation and proper review.",
    "Hindi and Kannada support uses word lists that no native speaker has reviewed yet; check those results carefully.",
]

PDF_LIMITATIONS: list[str] = [
    "This report is a preliminary investigative aid and requires human review. It is not evidence of identity.",
    NO_IDENTIFICATION,
    "Sketch versions are never overwritten: every version created for this case is listed in the version history.",
]
