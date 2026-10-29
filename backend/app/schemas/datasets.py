from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel, OutModel

DatasetKey = Literal["cufs", "cufsf", "uom_sgfs", "custom_attributes"]


class DatasetStatus(OutModel):
    key: str
    name: str
    kind: Literal["external", "custom"]
    description: str
    licence: str
    access: str = Field(description="How to obtain the data legitimately. Nothing is downloaded automatically.")
    citation: str
    source_url: str
    expected_path: str
    installed: bool = Field(description="Whether files are present in the expected folder right now.")
    inspected: bool
    last_inspected_at: datetime | None
    files_found: int | None = Field(description="From the last inspection; null = never inspected.")
    records: int = Field(description="Rows stored in the database by the last inspection.")
    valid_records: int
    labelled_records: int
    notes: list[str]
    translation_review: dict[str, int] | None = Field(
        default=None, description="Custom dataset only: number of rows per translation review status."
    )


class DatasetStatusResponse(OutModel):
    datasets: list[DatasetStatus]
    totals: dict[str, int]


class InspectRequest(ApiModel):
    dataset_key: DatasetKey | None = Field(default=None, description="Inspect one dataset, or all if omitted.")


class InspectProblem(OutModel):
    record: str
    problems: list[str]


class InspectResult(OutModel):
    dataset_key: str
    installed: bool
    files_found: int
    valid: int
    invalid: int
    truncated: bool
    summary: dict
    problems: list[InspectProblem]
    notes: list[str]
    inspected_at: datetime


class InspectResponse(OutModel):
    results: list[InspectResult]


class EvaluationRequest(ApiModel):
    evaluation_type: Literal["description_parser"] = "description_parser"
    split: Literal["dev", "test", "all"] = "all"
    only_reviewed_translations: bool = Field(
        default=False, description="Evaluate only rows whose translation was reviewed by a human."
    )


class AttributeMetric(OutModel):
    attribute: str
    n_labelled: int
    correct: int
    accuracy: float | None
    precision: float | None
    recall: float | None


class LanguageMetric(OutModel):
    language: str
    n: int
    exact_match: float | None
    mean_attribute_accuracy: float | None
    lexicon_review_status: str


class EvaluationOut(OutModel):
    id: int
    evaluation_type: str
    target_name: str
    target_version: str
    dataset_name: str
    dataset_version: str
    split: str
    n_examples: int
    metrics: dict
    notes: str | None
    status: str
    created_at: datetime
