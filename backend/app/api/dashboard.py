from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import ActivityLog, Case, InvestigatorNote, SketchVersion, User, WitnessDescription
from app.schemas.cases import ActivityOut, DashboardStats, StatusCounts
from app.services import cases as case_service

router = APIRouter(tags=["Dashboard"])


def _activity(db: Session, user: User, limit: int) -> list[ActivityOut]:
    stmt = select(ActivityLog, User.username).join(User, User.id == ActivityLog.user_id, isouter=True)
    if user.role != "admin":
        stmt = stmt.where(ActivityLog.user_id == user.id)
    rows = db.execute(stmt.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(limit)).all()
    return [ActivityOut(id=a.id, action=a.action, summary=a.summary, case_ref=a.case_ref, username=name, created_at=a.created_at) for a, name in rows]


@router.get(
    "/dashboard", response_model=DashboardStats, summary="Dashboard numbers",
    description="Every number is counted from the database at request time. Administrators see all cases; everyone else sees their own.",
)
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DashboardStats:
    admin = user.role == "admin"
    case_filter = [] if admin else [Case.owner_id == user.id]
    own_case_ids = select(Case.id).where(*case_filter)

    status = dict(db.execute(select(Case.status, func.count()).where(*case_filter).group_by(Case.status)).all())
    total = sum(status.values())
    with_selected = db.scalar(select(func.count(func.distinct(SketchVersion.case_pk))).where(SketchVersion.is_selected.is_(True), SketchVersion.case_pk.in_(own_case_ids))) or 0
    descriptions = db.scalar(select(func.count(WitnessDescription.id)).where(WitnessDescription.case_pk.in_(own_case_ids))) or 0
    versions = db.scalar(select(func.count(SketchVersion.id)).where(SketchVersion.case_pk.in_(own_case_ids))) or 0
    ai = db.scalar(select(func.count(SketchVersion.id)).where(SketchVersion.case_pk.in_(own_case_ids), SketchVersion.is_ai_generated.is_(True))) or 0
    notes = db.scalar(select(func.count(InvestigatorNote.id)).where(InvestigatorNote.case_pk.in_(own_case_ids))) or 0
    recent = db.scalars(select(Case).where(*case_filter).order_by(Case.updated_at.desc(), Case.id.desc()).limit(5)).all()
    return DashboardStats(
        scope="all" if admin else "own", total_cases=total,
        status_counts=StatusCounts(in_progress=status.get("in_progress", 0), under_review=status.get("under_review", 0), closed=status.get("closed", 0)),
        cases_with_selected_sketch=with_selected, witness_descriptions=descriptions, sketch_versions=versions,
        schematic_versions=versions - ai, ai_versions=ai, notes=notes,
        recent_cases=case_service.summaries_for(db, list(recent)), recent_activity=_activity(db, user, 8),
    )  # fmt: skip


@router.get("/activity", response_model=list[ActivityOut], summary="Recent activity (from the audit log)")
def activity(limit: int = Query(default=20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ActivityOut]:
    return _activity(db, user, limit)
