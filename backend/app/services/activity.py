"""Audit trail. The dashboard's "recent activity" list reads straight from these rows."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ActivityLog, Case, User


def log_activity(db: Session, *, user: User | None, action: str, summary: str, case: Case | None = None, case_ref: str | None = None) -> None:
    """Queue an activity row (the caller commits). Never put witness text in ``summary``."""
    db.add(
        ActivityLog(
            user_id=user.id if user else None,
            case_pk=case.id if case else None,
            case_ref=case.case_id if case else case_ref,
            action=action,
            summary=summary[:300],
        )
    )
