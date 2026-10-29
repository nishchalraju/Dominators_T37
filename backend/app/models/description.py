from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utcnow


class WitnessDescription(Base):
    """A witness's description of a face.

    ``original_text`` is never edited after it is saved. The parser's output is
    kept in ``extracted_attributes``; what the investigator accepted or corrected
    lives in ``confirmed_attributes`` (both are *estimates*, not facts).
    """

    __tablename__ = "witness_descriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_pk: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(60), default="Witness 1")  # who gave it; defaults to the case's witness name
    language: Mapped[str] = mapped_column(String(5))  # en | kn | hi
    original_text: Mapped[str] = mapped_column(Text)
    extracted_attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    confirmed_attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    additional_details: Mapped[str] = mapped_column(Text, default="")  # free text; used by AI engines only
    parse_details: Mapped[list] = mapped_column(JSON, default=list)  # evidence for each extracted value
    unrecognized: Mapped[list] = mapped_column(JSON, default=list)  # phrases that were NOT converted
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    parser_version: Mapped[str] = mapped_column(String(40), default="")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    case = relationship("Case", back_populates="descriptions")

    __table_args__ = (Index("ix_descriptions_case_created", "case_pk", "created_at"),)
