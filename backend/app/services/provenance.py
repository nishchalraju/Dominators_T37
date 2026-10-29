"""How an image describes its own origin (caption band on downloads and in the PDF report)."""

from __future__ import annotations

from app.models import SketchVersion
from app.services.disclaimers import PRELIMINARY
from app.services.sketch_models.registry import ENGINE_LABELS


def caption_for(version: SketchVersion, case_ref: str) -> tuple[str, list[str], bool]:
    """Returns ``(headline, lines, is_warning)``."""
    if version.is_ai_generated:
        headline, warning = "AI-GENERATED IMAGE - REQUIRES HUMAN REVIEW", True
        method = f"Made by an AI model ({version.model_name or version.engine}); details may be invented."
    else:
        headline, warning = "SCHEMATIC COMPOSITE - NOT AI-GENERATED", False
        method = "Drawn by fixed rules from the listed attributes; not a likeness of a real person."
    when = version.created_at.strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"Case {case_ref} | Version {version.version_number} | {ENGINE_LABELS.get(version.engine, version.engine)}",
        f"Created {when}",
        method,
        PRELIMINARY + " Not an identification.",
    ]
    return headline, lines, warning
