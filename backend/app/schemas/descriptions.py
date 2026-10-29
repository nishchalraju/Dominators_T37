from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import (
    AdditionalDetails,
    ApiModel,
    OutModel,
    check_attributes,
    check_language,
)

MAX_TEXT = 4000


class ParseRequest(ApiModel):
    text: str = Field(min_length=3, max_length=MAX_TEXT, description="The witness description (English, Kannada or Hindi).")
    language: str = Field(default="en", description="en, kn or hi")

    @field_validator("language")
    @classmethod
    def _lang(cls, value: str) -> str:
        return check_language(value)


class ExtractedValueOut(OutModel):
    attribute: str
    value: str
    evidence: str = Field(description="Words copied from the witness text that caused this value.")
    language: str
    match_type: str
    note: str | None = None


class UnrecognizedOut(OutModel):
    text: str
    reason: str


class ConflictOut(OutModel):
    attribute: str
    values: list[str]
    evidence: list[str]


class ParseResponse(OutModel):
    attributes: dict[str, str | None]
    details: list[ExtractedValueOut]
    unrecognized: list[UnrecognizedOut]
    conflicts: list[ConflictOut]
    warnings: list[str]
    declared_language: str
    detected_scripts: list[str]
    parser_name: str
    parser_version: str
    lexicon_status: dict[str, str] = Field(description="Review status of each language's word list.")
    notice: str = Field(description="Reminder that the output is an editable estimate.")


class DescriptionCreate(ApiModel):
    label: str = Field(
        default="Witness 1", min_length=1, max_length=60,
        description="Who gave this description, for example the witness's name or 'Witness 2'. It is printed in the report.",
    )
    language: str = "en"
    original_text: str = Field(min_length=3, max_length=MAX_TEXT)
    confirmed_attributes: dict[str, str | None] | None = Field(
        default=None, description="The attributes after the investigator reviewed them. Defaults to the parser's output."
    )
    additional_details: AdditionalDetails = ""

    @field_validator("language")
    @classmethod
    def _lang(cls, value: str) -> str:
        return check_language(value)

    @field_validator("confirmed_attributes")
    @classmethod
    def _attrs(cls, value):  # noqa: ANN001
        return None if value is None else check_attributes(value)


class DescriptionUpdate(ApiModel):
    """Only the reviewed attributes can change. The original text is never edited."""

    confirmed_attributes: dict[str, str | None]
    additional_details: AdditionalDetails = ""

    @field_validator("confirmed_attributes")
    @classmethod
    def _attrs(cls, value):  # noqa: ANN001
        return check_attributes(value)


class DescriptionOut(OutModel):
    id: int
    label: str
    language: str
    original_text: str
    extracted_attributes: dict[str, str | None]
    confirmed_attributes: dict[str, str | None]
    additional_details: str
    parse_details: list[ExtractedValueOut]
    unrecognized: list[UnrecognizedOut]
    warnings: list[str]
    parser_version: str
    created_at: datetime
    updated_at: datetime
    review_status: Literal["parser_output", "edited_by_investigator"] = "parser_output"
