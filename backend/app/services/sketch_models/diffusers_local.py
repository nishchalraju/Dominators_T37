"""Optional local inference with the ``diffusers`` library (EXPERIMENTAL, untested in this build).

Needs a GPU with plenty of memory and the extra packages in ``requirements-ai-local.txt``. It is only used
when ``AI_PROVIDER=diffusers`` is set explicitly. It exists so the adapter interface is proven to support a
local model; it has not been run here (this machine has no GPU).
"""

from __future__ import annotations

import importlib.util
import logging

from app.core.config import Settings, get_settings
from app.services.image_tools import ImageValidationError, pil_to_png
from app.services.sketch_models.base import (
    EditRequest,
    GenerationRequest,
    ModelOutput,
    ModelOutputError,
    ModelRequestError,
    ModelStatus,
    ModelUnavailableError,
    SketchModel,
    apply_health,
    record_failure,
    record_success,
)
from app.services.sketch_models.prompts import build_edit_prompt, build_generation_prompt

log = logging.getLogger("sketchassist.models.local")

SETUP_STEPS = [
    "Install a CUDA build of PyTorch for your GPU (https://pytorch.org/get-started/locally/).",
    "Run: pip install -r requirements-ai-local.txt",
    "Set AI_PROVIDER=diffusers (and optionally LOCAL_T2I_MODEL / LOCAL_EDIT_MODEL) in backend/.env, then restart.",
    "The first request downloads the model weights from Hugging Face (several GB). Check each model's licence first.",
]


class DiffusersLocalModel(SketchModel):
    engine = "diffusers"
    label = "Local diffusers model (AI, experimental)"
    is_ai = True

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._pipes: dict[str, object] = {}

    @staticmethod
    def _packages_present() -> bool:
        return all(importlib.util.find_spec(name) is not None for name in ("torch", "diffusers"))

    def status(self) -> ModelStatus:
        s = self._settings
        models = {"generate": s.local_t2i_model, "edit": s.local_edit_model}
        if not self._packages_present():
            return apply_health(
                ModelStatus(
                    engine=self.engine, label=self.label, is_ai=True, state="setup_required",
                    detail="The 'torch' and 'diffusers' packages are not installed.",
                    setup_steps=SETUP_STEPS, models=models,
                    licence_note="Check the licence of the model you choose; some forbid law-enforcement or biometric use.",
                )
            )
        return apply_health(
            ModelStatus(
                engine=self.engine, label=self.label, is_ai=True, state="ready",
                detail="Packages found. Not verified: the first request downloads weights and needs enough GPU memory.",
                models=models,
                licence_note="Check the licence of the model you choose; some forbid law-enforcement or biometric use.",
            )
        )

    def _device(self) -> str:
        import torch

        if self._settings.local_device != "auto":
            return self._settings.local_device
        return "cuda" if torch.cuda.is_available() else "cpu"

    def _pipeline(self, kind: str):
        if not self._packages_present():
            raise ModelUnavailableError(self.engine, "Local inference packages are not installed.", SETUP_STEPS)
        if kind not in self._pipes:
            import torch
            from diffusers import AutoPipelineForImage2Image, AutoPipelineForText2Image

            device = self._device()
            dtype = torch.bfloat16 if device == "cuda" else torch.float32
            name = self._settings.local_t2i_model if kind == "t2i" else self._settings.local_edit_model
            cls = AutoPipelineForText2Image if kind == "t2i" else AutoPipelineForImage2Image
            self._pipes[kind] = cls.from_pretrained(name, torch_dtype=dtype).to(device)
        return self._pipes[kind]

    def _finish(self, image) -> bytes:
        try:
            png = pil_to_png(image, max_pixels=self._settings.max_image_pixels, max_side=self._settings.stored_image_max_side)
        except (ImageValidationError, ValueError, OSError) as exc:
            raise ModelOutputError(self.engine, "The local model did not return a valid image.") from exc
        self.validate_image(png)
        record_success(self.engine)
        return png

    def generate(self, request: GenerationRequest) -> ModelOutput:
        prompt, negative = build_generation_prompt(request.attributes, request.additional_details)
        try:
            pipe = self._pipeline("t2i")
            image = pipe(prompt=prompt, num_inference_steps=self._settings.local_steps, width=1024, height=1024).images[0]
        except ModelUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            record_failure(self.engine, type(exc).__name__)
            raise ModelRequestError(self.engine, f"The local model failed ({type(exc).__name__}). See the server log.") from exc
        return ModelOutput(
            png=self._finish(image), engine=self.engine, is_ai_generated=True, model_name=self._settings.local_t2i_model,
            prompt_used=prompt, params={"steps": self._settings.local_steps}, notes=["Generated by a local AI model (experimental)."],
        )

    def edit(self, request: EditRequest) -> ModelOutput:
        import io

        from PIL import Image

        prompt = build_edit_prompt(request.instruction, request.change_summary_en, request.new_attributes, request.additional_details)
        try:
            pipe = self._pipeline("edit")
            base = Image.open(io.BytesIO(request.base_png)).convert("RGB")
            image = pipe(prompt=prompt, image=base, num_inference_steps=self._settings.local_steps).images[0]
        except ModelUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            record_failure(self.engine, type(exc).__name__)
            raise ModelRequestError(self.engine, f"The local model failed ({type(exc).__name__}). See the server log.") from exc
        return ModelOutput(
            png=self._finish(image), engine=self.engine, is_ai_generated=True, model_name=self._settings.local_edit_model,
            prompt_used=prompt, params={"steps": self._settings.local_steps}, notes=["Edited by a local AI model (experimental)."],
        )
