"""Hosted open-weight models through Hugging Face Inference Providers.

Default models (both Apache-2.0, ungated): ``Qwen/Qwen-Image`` for text-to-image and
``Qwen/Qwen-Image-Edit`` for editing. They are run by third-party providers; you need a
Hugging Face token (``HF_TOKEN``) with permission to call Inference Providers.

This adapter has been unit-tested with a stand-in client only. It has NOT been run against
the live service in this build (no token was available) - see docs/MODEL_SELECTION.md.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx
from PIL import Image

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

log = logging.getLogger("sketchassist.models.hf")

SETUP_STEPS = [
    "Create a Hugging Face account and a fine-grained access token that is allowed to call Inference Providers "
    "(https://huggingface.co/settings/tokens).",
    "Put it in backend/.env as HF_TOKEN=... (never in frontend code) and restart the backend.",
    "Optional: choose a provider with HF_PROVIDER (default 'auto') and different models with HF_T2I_MODEL / HF_EDIT_MODEL.",
    "Provider usage is billed to or limited by your Hugging Face account.",
]
LICENCE_NOTE = (
    "Default models Qwen/Qwen-Image and Qwen/Qwen-Image-Edit are Apache-2.0. If you change the model IDs, read the new "
    "model's licence first: some (for example Stable Diffusion 1.x/2.x and FLUX.1 [dev]) prohibit law-enforcement, "
    "surveillance or biometric uses."
)


def _default_client_factory(settings: Settings):
    from huggingface_hub import InferenceClient  # imported lazily: heavy and optional

    return InferenceClient(
        provider=settings.hf_provider or "auto",  # type: ignore[arg-type]
        api_key=settings.hf_token,
        timeout=settings.ai_timeout_seconds,
    )


def explain_http_status(status: int | None, detail: str = "") -> tuple[str, bool]:
    """User-facing explanation and whether trying again later may help."""
    if status in (401, 403):
        return "The provider rejected the credentials. Check that the token is valid and allowed to call Inference Providers.", False
    if status == 402:
        return "The provider reports that credits or quota are used up for this account.", False
    if status == 404:
        return "The provider does not serve this model (HTTP 404). Check HF_T2I_MODEL / HF_EDIT_MODEL and HF_PROVIDER.", False
    if status == 400 or status == 422:
        return f"The provider rejected the request as invalid{': ' + detail if detail else ''}.", False
    if status == 429:
        return "Rate limit reached. Wait a little and try again.", True
    if status is not None and status >= 500:
        return "The provider had a server error. Try again in a moment.", True
    return "The request to the model provider failed.", True


class HuggingFaceModel(SketchModel):
    engine = "huggingface"
    label = "Hugging Face Inference Providers (AI)"
    is_ai = True

    def __init__(self, settings: Settings | None = None, client_factory: Callable[[Settings], Any] | None = None):
        self._settings = settings or get_settings()
        self._client_factory = client_factory or _default_client_factory  # tests pass a stand-in client

    # ----- status ------------------------------------------------------------
    def configured(self) -> bool:
        return bool(self._settings.hf_token)

    def status(self) -> ModelStatus:
        s = self._settings
        models = {"generate": s.hf_t2i_model, "edit": s.hf_edit_model}
        if not self.configured():
            return apply_health(
                ModelStatus(
                    engine=self.engine, label=self.label, is_ai=True, state="setup_required",
                    detail="No HF_TOKEN is configured, so this engine cannot run.",
                    setup_steps=SETUP_STEPS, models=models, licence_note=LICENCE_NOTE,
                )
            )
        return apply_health(
            ModelStatus(
                engine=self.engine, label=self.label, is_ai=True, state="ready",
                detail=f"Token configured (provider: {s.hf_provider}). Reachability is only confirmed after a first successful request.",
                models=models, licence_note=LICENCE_NOTE,
            )
        )

    def _client(self):
        if not self.configured():
            raise ModelUnavailableError(self.engine, "Hugging Face is not set up (HF_TOKEN is missing).", SETUP_STEPS)
        return self._client_factory(self._settings)

    # ----- calls ----------------------------------------------------------------
    def _run(self, call: Callable[[Any], Image.Image]) -> bytes:
        try:
            image = call(self._client())
        except ModelUnavailableError:
            raise
        except httpx.TimeoutException as exc:
            record_failure(self.engine, "timeout")
            raise ModelRequestError(self.engine, "The model provider took too long to answer. Try again.", retryable=True) from exc
        except httpx.TransportError as exc:
            record_failure(self.engine, "network error")
            raise ModelRequestError(self.engine, "Could not reach the model provider (network error).", retryable=True) from exc
        except Exception as exc:  # noqa: BLE001 - provider libraries raise many types
            status = getattr(getattr(exc, "response", None), "status_code", None)
            name = type(exc).__name__
            if "Timeout" in name:
                message, retry = "The model provider took too long to answer. Try again.", True
            elif "Overloaded" in name:
                message, retry = "The model is overloaded right now. Try again shortly.", True
            else:
                message, retry = explain_http_status(status)
            log.warning("Hugging Face call failed (%s, status=%s)", name, status)  # never log the token or prompt
            record_failure(self.engine, f"{name} {status or ''}".strip())
            raise ModelRequestError(self.engine, message, status=status, retryable=retry) from exc
        try:
            png = pil_to_png(image, max_pixels=self._settings.max_image_pixels, max_side=self._settings.stored_image_max_side)
        except (ImageValidationError, AttributeError, ValueError, OSError) as exc:
            record_failure(self.engine, "invalid image returned")
            raise ModelOutputError(self.engine, "The provider answered, but the result was not a valid image.") from exc
        _reject_blank(self.engine, png)
        self.validate_image(png)
        record_success(self.engine)
        return png

    def generate(self, request: GenerationRequest) -> ModelOutput:
        prompt, negative = build_generation_prompt(request.attributes, request.additional_details)
        model = self._settings.hf_t2i_model
        kwargs: dict[str, Any] = {"model": model, "negative_prompt": negative}
        if request.seed is not None:
            kwargs["seed"] = request.seed
        png = self._run(lambda client: client.text_to_image(prompt, **kwargs))
        return ModelOutput(
            png=png, engine=self.engine, is_ai_generated=True, model_name=model, prompt_used=prompt,
            params={"provider": self._settings.hf_provider, "negative_prompt": negative, "seed": request.seed},
            notes=["Generated by an AI model through Hugging Face Inference Providers. Review the result by eye."],
        )

    def edit(self, request: EditRequest) -> ModelOutput:
        prompt = build_edit_prompt(request.instruction, request.change_summary_en, request.new_attributes, request.additional_details)
        model = self._settings.hf_edit_model
        png = self._run(lambda client: client.image_to_image(request.base_png, prompt=prompt, model=model))
        notes = ["Edited by an AI model through Hugging Face Inference Providers. Review the result by eye."]
        if request.instruction_language != "en":
            notes.append(
                "The instruction was not in English. The model received an English summary of the recognised changes "
                "plus your original text; understanding of Hindi / Kannada text has not been tested."
            )
        return ModelOutput(
            png=png, engine=self.engine, is_ai_generated=True, model_name=model, prompt_used=prompt,
            params={"provider": self._settings.hf_provider}, notes=notes,
        )


def _reject_blank(engine: str, png: bytes) -> None:
    """A completely uniform image is a failed generation, not a sketch."""
    import io

    from PIL import ImageStat

    with Image.open(io.BytesIO(png)) as img:
        stat = ImageStat.Stat(img.convert("L"))
    if max(stat.stddev) < 2.0:
        record_failure(engine, "blank image returned")
        raise ModelOutputError(engine, "The model returned a blank image. Try again.")
