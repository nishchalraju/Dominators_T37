"""The schematic engine: a rule-based drawing. It is NOT artificial intelligence."""

from __future__ import annotations

from app.services.attributes import ATTRIBUTE_BY_KEY
from app.services.sketch_models.base import (
    EditRequest,
    GenerationRequest,
    ModelOutput,
    ModelStatus,
    SketchModel,
    apply_health,
    record_success,
)
from app.services.sketch_models.schematic_renderer import RENDERER_VERSION, render_schematic

NOT_AI_NOTE = (
    "Schematic composite drawn by fixed rules from the attribute values. It is not AI-generated and "
    "is not a likeness of any real person. Features you did not specify are drawn in a neutral form."
)


class SchematicModel(SketchModel):
    engine = "schematic"
    label = "Schematic composite (rule-based, not AI)"
    is_ai = False

    def status(self) -> ModelStatus:
        return apply_health(
            ModelStatus(
                engine=self.engine,
                label=self.label,
                is_ai=False,
                state="ready",
                detail="Always available. Draws a generic diagram from the attributes; every attribute changes the picture.",
                models={"generate": f"schematic-renderer {RENDERER_VERSION}", "edit": f"schematic-renderer {RENDERER_VERSION}"},
                licence_note="Own code, no external model. Pillow (HPND) is used for drawing.",
            )
        )

    def _render(self, attributes) -> ModelOutput:
        result = render_schematic(attributes)
        self.validate_image(result.png)
        record_success(self.engine)
        notes = [NOT_AI_NOTE, *result.notes]
        if result.unspecified:
            labels = [ATTRIBUTE_BY_KEY[k].label.lower() for k in result.unspecified]
            notes.append("Drawn with neutral defaults for: " + ", ".join(labels) + ".")
        return ModelOutput(
            png=result.png,
            engine=self.engine,
            is_ai_generated=False,
            model_name=f"schematic-renderer {RENDERER_VERSION}",
            prompt_used=None,
            params={"seed": result.seed, "unspecified": result.unspecified, "renderer_version": RENDERER_VERSION},
            notes=notes,
        )

    def generate(self, request: GenerationRequest) -> ModelOutput:
        return self._render(request.attributes)

    def edit(self, request: EditRequest) -> ModelOutput:
        # A revision re-draws from the updated attributes. The earlier image is untouched.
        return self._render(request.new_attributes)
