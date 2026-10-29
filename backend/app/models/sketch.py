from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utcnow


class SketchVersion(Base):
    """One saved sketch image.

    Versions are append-only: a revision creates a NEW row and a NEW file, so an
    earlier sketch is never overwritten.
    """

    __tablename__ = "sketch_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_pk: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    description_id: Mapped[int | None] = mapped_column(ForeignKey("witness_descriptions.id", ondelete="SET NULL"))
    version_number: Mapped[int] = mapped_column(Integer)  # 1, 2, 3 ... within the case
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("sketch_versions.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(12))  # initial | revision
    instruction: Mapped[str] = mapped_column(Text, default="")
    instruction_language: Mapped[str | None] = mapped_column(String(5))
    target_attribute: Mapped[str | None] = mapped_column(String(40))
    revision_details: Mapped[dict] = mapped_column(JSON, default=dict)  # parsed changes / ignored parts of the instruction
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)  # snapshot used for this version
    attributes_note: Mapped[str | None] = mapped_column(Text)

    # How the image was produced - stored so reports can state it honestly.
    engine: Mapped[str] = mapped_column(String(20))  # schematic | huggingface | openai | diffusers
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    model_name: Mapped[str | None] = mapped_column(String(200))
    model_params: Mapped[dict] = mapped_column(JSON, default=dict)
    prompt_used: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[list] = mapped_column(JSON, default=list)  # engine statements, e.g. "not AI-generated"
    additional_details: Mapped[str] = mapped_column(Text, default="")

    # Managed file reference (relative to the storage dir) - never a user-supplied path.
    image_path: Mapped[str] = mapped_column(String(300))
    image_sha256: Mapped[str] = mapped_column(String(64))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    file_size: Mapped[int] = mapped_column(Integer)

    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    case = relationship("Case", back_populates="sketches")
    parent = relationship("SketchVersion", remote_side="SketchVersion.id")

    __table_args__ = (
        UniqueConstraint("case_pk", "version_number", name="uq_sketch_case_version"),
        # at most one "selected for report" sketch per case
        Index(
            "uq_sketch_one_selected_per_case",
            "case_pk",
            unique=True,
            sqlite_where=text("is_selected = 1"),
        ),
    )
