"""Case helpers: ID generation, authorisation, summaries."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Case, InvestigatorNote, SketchVersion, User, WitnessDescription
from app.schemas.cases import CaseDetail, CaseSummary

# No 0/O/1/I/L: easier to read aloud and to copy from a printout.
_ID_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def new_case_id(db: Session) -> str:
    """``SA-<year>-<6 random characters>``, checked for uniqueness (the DB constraint is the final guard)."""
    year = datetime.now(timezone.utc).year
    for _ in range(20):
        candidate = f"SA-{year}-" + "".join(secrets.choice(_ID_ALPHABET) for _ in range(6))
        if db.scalar(select(Case.id).where(Case.case_id == candidate)) is None:
            return candidate
    raise AppError(500, "Could not create a unique case ID. Please try again.", "case_id_unavailable")


def get_case_or_404(db: Session, case_id: str, user: User) -> Case:
    """Owner or admin only. A case that is not yours looks exactly like one that does not exist."""
    case = db.scalar(select(Case).where(Case.case_id == case_id.strip().upper()))
    if case is None or (case.owner_id != user.id and user.role != "admin"):
        raise AppError(404, "Case not found.", "case_not_found")
    return case


def require_open(case: Case) -> None:
    if case.status == "closed":
        raise AppError(409, "This case is closed. Reopen it before making changes.", "case_closed")


def selected_sketch_id(db: Session, case_pk: int) -> int | None:
    return db.scalar(select(SketchVersion.id).where(SketchVersion.case_pk == case_pk, SketchVersion.is_selected.is_(True)))


def _counts(db: Session, case_pk: int) -> tuple[int, int, int]:
    d = db.scalar(select(func.count(WitnessDescription.id)).where(WitnessDescription.case_pk == case_pk)) or 0
    s = db.scalar(select(func.count(SketchVersion.id)).where(SketchVersion.case_pk == case_pk)) or 0
    n = db.scalar(select(func.count(InvestigatorNote.id)).where(InvestigatorNote.case_pk == case_pk)) or 0
    return d, s, n


def summarize(db: Session, case: Case) -> CaseSummary:
    d, s, _ = _counts(db, case.id)
    return CaseSummary(
        case_id=case.case_id, title=case.title, incident_date=case.incident_date, status=case.status,  # type: ignore[arg-type]
        investigator_ref=case.investigator_ref, investigator_name=case.investigator_name or "", witness_name=case.witness_name or "",
        created_at=case.created_at, updated_at=case.updated_at, description_count=d, sketch_count=s, selected_sketch_id=selected_sketch_id(db, case.id),
    )  # fmt: skip


def detail(db: Session, case: Case) -> CaseDetail:
    base = summarize(db, case)
    _, _, n = _counts(db, case.id)
    owner = db.get(User, case.owner_id)
    return CaseDetail(**base.model_dump(), incident_description=case.incident_description, note_count=n,
                      owner_username=owner.username if owner else None)  # fmt: skip


def summaries_for(db: Session, cases: list[Case]) -> list[CaseSummary]:
    """Summaries for many cases using three grouped queries instead of three per case."""
    if not cases:
        return []
    ids = [c.id for c in cases]
    descriptions = dict(db.execute(select(WitnessDescription.case_pk, func.count()).where(WitnessDescription.case_pk.in_(ids)).group_by(WitnessDescription.case_pk)).all())
    sketches = dict(db.execute(select(SketchVersion.case_pk, func.count()).where(SketchVersion.case_pk.in_(ids)).group_by(SketchVersion.case_pk)).all())
    selected = dict(db.execute(select(SketchVersion.case_pk, SketchVersion.id).where(SketchVersion.case_pk.in_(ids), SketchVersion.is_selected.is_(True))).all())
    return [
        CaseSummary(
            case_id=c.case_id, title=c.title, incident_date=c.incident_date, status=c.status,  # type: ignore[arg-type]
            investigator_ref=c.investigator_ref, investigator_name=c.investigator_name or "", witness_name=c.witness_name or "",
            created_at=c.created_at, updated_at=c.updated_at, description_count=descriptions.get(c.id, 0), sketch_count=sketches.get(c.id, 0), selected_sketch_id=selected.get(c.id),
        )
        for c in cases
    ]  # fmt: skip
