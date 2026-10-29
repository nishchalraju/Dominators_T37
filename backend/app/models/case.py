from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utcnow

CASE_STATUSES = ("in_progress", "under_review", "closed")


class Case(Base):
    """One investigation. Everything else (descriptions, sketches, notes) hangs off a case."""

    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # e.g. SA-2026-7K3QWP
    title: Mapped[str] = mapped_column(String(200), index=True)
    incident_date: Mapped[date] = mapped_column(Date)
    incident_description: Mapped[str] = mapped_column(Text, default="")
    investigator_ref: Mapped[str] = mapped_column(String(64))  # badge / file reference
    # Names are personal data. They are optional for cases created before they existed ("" = not recorded).
    # server_default lets the startup upgrade add these columns to a database that already holds cases.
    investigator_name: Mapped[str] = mapped_column(String(120), default="", server_default="")
    witness_name: Mapped[str] = mapped_column(String(120), default="", server_default="")
    status: Mapped[str] = mapped_column(String(20), default="in_progress", index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="cases")
    descriptions = relationship(
        "WitnessDescription", back_populates="case", cascade="all, delete-orphan", order_by="WitnessDescription.id"
    )
    sketches = relationship(
        "SketchVersion", back_populates="case", cascade="all, delete-orphan", order_by="SketchVersion.version_number"
    )
    notes = relationship(
        "InvestigatorNote", back_populates="case", cascade="all, delete-orphan", order_by="InvestigatorNote.id"
    )

    __table_args__ = (Index("ix_cases_owner_updated", "owner_id", "updated_at"),)
