from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UTCDateTime, utcnow


class ActivityLog(Base):
    """Audit trail of real actions. The dashboard's "recent activity" reads from here."""

    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    case_pk: Mapped[int | None] = mapped_column(ForeignKey("cases.id", ondelete="SET NULL"), index=True)
    case_ref: Mapped[str | None] = mapped_column(String(32), index=True)  # public case ID; survives case deletion
    action: Mapped[str] = mapped_column(String(40), index=True)
    summary: Mapped[str] = mapped_column(String(300))  # never contains witness text
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
