from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import ApiModel, OutModel

CaseStatus = Literal["in_progress", "under_review", "closed"]
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _./-]{0,63}$")


# "_" is allowed because the investigator name is suggested from the account, and user names may contain it.
_NAME_PUNCTUATION = set(" .,'\u2019-()/_")
_INDIC_JOINERS = {"\u200c", "\u200d"}  # zero-width (non-)joiners: part of many Hindi / Kannada names


def clean_person_name(value: str, what: str) -> str:
    """Trim, collapse spaces and check a person's name.

    Letters of ANY script are fine (the check uses Unicode categories, because Python's ``\\w`` rejects the vowel
    signs and virama of Hindi and Kannada names). Digits are allowed so a neutral code such as ``W-01`` works when
    a witness's name must be withheld. Angle brackets, quotes, control characters and other symbols are not.
    """
    cleaned = " ".join(value.split())
    if len(cleaned) < 2:
        raise ValueError(f"{what} needs at least 2 characters.")
    if not any(unicodedata.category(ch).startswith("L") for ch in cleaned):
        raise ValueError(f"{what} must contain letters (or a code such as W-01).")
    bad = sorted({ch for ch in cleaned if unicodedata.category(ch)[0] not in "LMN" and ch not in _NAME_PUNCTUATION and ch not in _INDIC_JOINERS})
    if bad:
        raise ValueError(f"{what} contains characters that are not allowed: {' '.join(bad[:6])}")
    return cleaned


def _not_future(value: date) -> date:
    if value > datetime.now(timezone.utc).date() + timedelta(days=1):
        raise ValueError("The incident date cannot be in the future.")
    if value.year < 1970:
        raise ValueError("The incident date is not plausible.")
    return value


class CaseCreate(ApiModel):
    title: str = Field(min_length=3, max_length=200)
    incident_date: date
    incident_description: str = Field(default="", max_length=5000)
    investigator_ref: str = Field(
        min_length=1, max_length=64, description="Your reference or badge number (letters, digits, space, - _ . /)."
    )
    investigator_name: str = Field(min_length=2, max_length=120, description="Name of the investigator in charge of this case.")
    witness_name: str = Field(
        min_length=2, max_length=120,
        description="Name of the witness who gave the description. Use a neutral code such as W-01 if the name must be withheld.",
    )

    @field_validator("incident_date")
    @classmethod
    def _date(cls, value: date) -> date:
        return _not_future(value)

    @field_validator("investigator_name")
    @classmethod
    def _investigator_name(cls, value: str) -> str:
        return clean_person_name(value, "The investigator name")

    @field_validator("witness_name")
    @classmethod
    def _witness_name(cls, value: str) -> str:
        return clean_person_name(value, "The witness name")

    @field_validator("investigator_ref")
    @classmethod
    def _ref(cls, value: str) -> str:
        if not REF_RE.match(value):
            raise ValueError("Use only letters, digits, spaces and - _ . / in the reference.")
        return value


class CaseUpdate(ApiModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    incident_date: date | None = None
    incident_description: str | None = Field(default=None, max_length=5000)
    investigator_ref: str | None = Field(default=None, min_length=1, max_length=64)
    investigator_name: str | None = Field(default=None, min_length=2, max_length=120)
    witness_name: str | None = Field(default=None, min_length=2, max_length=120)
    status: CaseStatus | None = None

    @field_validator("investigator_name")
    @classmethod
    def _investigator_name(cls, value: str | None) -> str | None:
        return None if value is None else clean_person_name(value, "The investigator name")

    @field_validator("witness_name")
    @classmethod
    def _witness_name(cls, value: str | None) -> str | None:
        return None if value is None else clean_person_name(value, "The witness name")

    @field_validator("incident_date")
    @classmethod
    def _date(cls, value: date | None) -> date | None:
        return _not_future(value) if value else value

    @field_validator("investigator_ref")
    @classmethod
    def _ref(cls, value: str | None) -> str | None:
        if value is not None and not REF_RE.match(value):
            raise ValueError("Use only letters, digits, spaces and - _ . / in the reference.")
        return value


class CaseSummary(OutModel):
    case_id: str
    title: str
    incident_date: date
    status: CaseStatus
    investigator_ref: str
    investigator_name: str = ""  # "" = not recorded (cases created before names existed)
    witness_name: str = ""
    created_at: datetime
    updated_at: datetime
    description_count: int = 0
    sketch_count: int = 0
    selected_sketch_id: int | None = None


class CaseDetail(CaseSummary):
    incident_description: str
    note_count: int = 0
    owner_username: str | None = None


class CaseList(OutModel):
    items: list[CaseSummary]
    total: int
    page: int
    page_size: int


class NoteCreate(ApiModel):
    body: str = Field(min_length=1, max_length=2000)
    sketch_version_id: int | None = Field(default=None, description="Optionally attach the note to a sketch version.")


class NoteOut(OutModel):
    id: int
    body: str
    sketch_version_id: int | None
    author_username: str | None
    created_at: datetime


class ActivityOut(OutModel):
    id: int
    action: str
    summary: str
    case_ref: str | None
    username: str | None
    created_at: datetime


class StatusCounts(OutModel):
    in_progress: int = 0
    under_review: int = 0
    closed: int = 0


class DashboardStats(OutModel):
    scope: Literal["own", "all"]
    total_cases: int
    status_counts: StatusCounts
    cases_with_selected_sketch: int
    witness_descriptions: int
    sketch_versions: int
    schematic_versions: int
    ai_versions: int
    notes: int
    recent_cases: list[CaseSummary]
    recent_activity: list[ActivityOut]
