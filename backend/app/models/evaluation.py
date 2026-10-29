from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UTCDateTime, utcnow


class ModelEvaluation(Base):
    """The stored result of one real evaluation run. Nothing is seeded or invented."""

    __tablename__ = "model_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_type: Mapped[str] = mapped_column(String(40), index=True)  # description_parser | ...
    target_name: Mapped[str] = mapped_column(String(120))  # what was evaluated
    target_version: Mapped[str] = mapped_column(String(60), default="")
    dataset_name: Mapped[str] = mapped_column(String(120))
    dataset_version: Mapped[str] = mapped_column(String(80), default="")  # content hash of the data used
    split: Mapped[str] = mapped_column(String(20), default="all")  # dev | test | all
    n_examples: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text)  # limitations of this particular run
    status: Mapped[str] = mapped_column(String(20), default="completed")
    run_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
