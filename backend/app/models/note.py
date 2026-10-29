from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utcnow


class InvestigatorNote(Base):
    """Append-only notes (they cannot be edited or deleted, to keep an audit trail)."""

    __tablename__ = "investigator_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_pk: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    sketch_version_id: Mapped[int | None] = mapped_column(ForeignKey("sketch_versions.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    case = relationship("Case", back_populates="notes")
    author = relationship("User")
