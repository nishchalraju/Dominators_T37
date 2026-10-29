"""Small building blocks shared by several schema modules."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.attributes import (
    LANGUAGE_CODES,
    MAX_ADDITIONAL_DETAILS,
    AttributeValidationError,
    clean_attributes,
)


class ApiModel(BaseModel):
    """Base class: rejects unknown fields so typos in requests are reported, not ignored."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OutModel(BaseModel):
    """Base class for responses built from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class ErrorBody(OutModel):
    detail: str
    code: str


class ValidationErrorBody(ErrorBody):
    fields: dict[str, str] = {}


Language = Annotated[str, Field(description="Language of the text: en (English), kn (Kannada) or hi (Hindi).")]


def check_language(value: str) -> str:
    if value not in LANGUAGE_CODES:
        raise ValueError(f"Language must be one of: {', '.join(LANGUAGE_CODES)}.")
    return value


def check_attributes(value: dict | None) -> dict[str, str]:
    try:
        return clean_attributes(value or {})  # type: ignore[return-value]
    except AttributeValidationError as exc:
        raise ValueError(str(exc)) from exc


class AttributesMixin(ApiModel):
    @field_validator("attributes", check_fields=False, mode="before")
    @classmethod
    def _attrs(cls, value):  # noqa: ANN001
        return check_attributes(value)


AdditionalDetails = Annotated[str, Field(max_length=MAX_ADDITIONAL_DETAILS)]
