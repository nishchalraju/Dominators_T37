from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UTCDateTime, utcnow


class DatasetRecord(Base):
    """One inventory entry found by the dataset inspector.

    For image datasets (CUFS, CUFSF, UoM-SGFS) there is one record per image file.
    For the custom attribute dataset there is one record per CSV row.
    Rows only exist if an inspection actually ran - nothing is pre-filled.
    """

    __tablename__ = "dataset_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_key: Mapped[str] = mapped_column(String(40), index=True)
    record_key: Mapped[str] = mapped_column(String(400))  # relative file path or "row:<sample_id>"
    source_id: Mapped[str] = mapped_column(String(200), default="")  # identifier from the source dataset
    kind: Mapped[str] = mapped_column(String(30), default="image")  # image | attribute_row
    has_image: Mapped[bool] = mapped_column(Boolean, default=False)
    image_readable: Mapped[bool] = mapped_column(Boolean, default=False)
    image_format: Mapped[str | None] = mapped_column(String(20))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    file_size: Mapped[int | None] = mapped_column(Integer)
    labelled: Mapped[bool] = mapped_column(Boolean, default=False)  # has attribute labels
    valid: Mapped[bool] = mapped_column(Boolean, default=True)
    problems: Mapped[list] = mapped_column(JSON, default=list)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    inspected_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    inspected_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    __table_args__ = (
        UniqueConstraint("dataset_key", "record_key", name="uq_dataset_record"),
        Index("ix_dataset_records_key_valid", "dataset_key", "valid"),
    )


class DatasetInspection(Base):
    """A summary of one inspection run (so the UI can show 'last inspected')."""

    __tablename__ = "dataset_inspections"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_key: Mapped[str] = mapped_column(String(40), index=True)
    installed: Mapped[bool] = mapped_column(Boolean, default=False)
    files_found: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text)
    inspected_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    inspected_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
