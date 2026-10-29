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

EngineChoice = Literal["ai", "schematic"]


class GenerateRequest(ApiModel):
    case_id: str = Field(description="Public case ID, e.g. SA-2026-7K3QWP.")
    description_id: int | None = Field(default=None, description="Use this saved description's reviewed attributes.")
    attributes: dict[str, str | None] | None = Field(
        default=None, description="Attributes to draw. Overrides the description's reviewed attributes if given."
    )
    additional_details: AdditionalDetails | None = None
    engine: EngineChoice = Field(
        description="'schematic' = rule-based drawing (not AI). 'ai' = the configured AI engine (needs setup)."
    )

    @field_validator("attributes")
    @classmethod
    def _attrs(cls, value):  # noqa: ANN001
        return None if value is None else check_attributes(value)


class ReviseRequest(ApiModel):
    instruction: str = Field(min_length=3, max_length=500, description="For example: 'make the eyebrows thicker and add glasses'.")
    language: str = "en"
    engine: EngineChoice | None = Field(
        default=None, description="Defaults to the kind of engine that made the sketch being revised."
    )

    @field_validator("language")
    @classmethod
    def _lang(cls, value: str) -> str:
        return check_language(value)


class ChangeOut(OutModel):
    attribute: str
    label: str
    before: str | None
    after: str
    evidence: str
    kind: str
    note: str | None = None


class IgnoredOut(OutModel):
    text: str
    reason: str


class RevisionDetails(OutModel):
    changes: list[ChangeOut] = []
    ignored: list[IgnoredOut] = []
    notes: list[str] = []


class SketchVersionOut(OutModel):
    id: int
    case_id: str = Field(description="Public case ID this sketch belongs to.")
    version_number: int
    parent_id: int | None
    parent_version_number: int | None = None
    kind: Literal["initial", "revision"]
    instruction: str
    instruction_language: str | None
    target_attribute: str | None
    attributes: dict[str, str | None]
    additional_details: str
    engine: str
    engine_label: str
    is_ai_generated: bool
    model_name: str | None
    notes: list[str]
    revision_details: RevisionDetails | None = None
    is_selected: bool
    created_by: str | None = None
    created_at: datetime
    width: int
    height: int
    file_size: int
    sha256: str
    image_url: str
    thumbnail_url: str
    download_url: str


class SketchVersionList(OutModel):
    case_id: str
    items: list[SketchVersionOut]


class EngineStatusOut(OutModel):
    engine: str
    label: str
    is_ai: bool
    state: Literal["ready", "setup_required", "disabled"]
    available: bool
    detail: str
    setup_steps: list[str]
    supports_generate: bool
    supports_edit: bool
    models: dict[str, str]
    licence_note: str | None
    verified: bool = Field(description="True only after a real request succeeded since the server started.")
    last_success_at: datetime | None
    last_error: str | None
    last_error_at: datetime | None
    last_evaluated_at: datetime | None = Field(default=None, description="From stored evaluations; null = never evaluated.")
