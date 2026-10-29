"""OpenAI Images API (or any compatible endpoint) over plain HTTPS.

Uses ``POST /images/generations`` (JSON) and ``POST /images/edits`` (multipart). The model name is
configurable (``OPENAI_IMAGE_MODEL``) because OpenAI renames models; the default may need updating.
Stand-in HTTP transport only in unit tests: this adapter was NOT run against the live API in this build.
"""

from __future__ import annotations

import base64
import binascii
import logging

import httpx

from app.core.config import Settings, get_settings
from app.services.image_tools import ImageValidationError, normalize_to_png
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
from app.services.sketch_models.huggingface import _reject_blank, explain_http_status
from app.services.sketch_models.prompts import build_edit_prompt, build_generation_prompt

log = logging.getLogger("sketchassist.models.openai")

SETUP_STEPS = [
    "Create an API key in your OpenAI account (https://platform.openai.com/api-keys).",
    "Put it in backend/.env as OPENAI_API_KEY=... (never in frontend code) and restart the backend.",
    "Image models may require organisation verification. If the default model name is rejected, set OPENAI_IMAGE_MODEL.",
    "Usage is billed to your OpenAI account and subject to OpenAI's usage policies.",
]
LICENCE_NOTE = "Commercial hosted service under OpenAI's terms and usage policies; generating realistic faces may be restricted."


class OpenAIImagesModel(SketchModel):
    engine = "openai"
    label = "OpenAI Images API (AI)"
    is_ai = True

    def __init__(self, settings: Settings | None = None, transport: httpx.BaseTransport | None = None):
        self._settings = settings or get_settings()
        self._transport = transport  # tests inject httpx.MockTransport

    def configured(self) -> bool:
        return bool(self._settings.openai_api_key)

    def status(self) -> ModelStatus:
        s = self._settings
        models = {"generate": s.openai_image_model, "edit": s.openai_image_model}
        if not self.configured():
            return apply_health(
                ModelStatus(
                    engine=self.engine, label=self.label, is_ai=True, state="setup_required",
                    detail="No OPENAI_API_KEY is configured, so this engine cannot run.",
                    setup_steps=SETUP_STEPS, models=models, licence_note=LICENCE_NOTE,
                )
            )
        return apply_health(
            ModelStatus(
                engine=self.engine, label=self.label, is_ai=True, state="ready",
                detail=f"API key configured ({s.openai_base_url}). Reachability is only confirmed after a first successful request.",
                models=models, licence_note=LICENCE_NOTE,
            )
        )

    def _post(self, path: str, **kwargs) -> bytes:
        if not self.configured():
            raise ModelUnavailableError(self.engine, "OpenAI is not set up (OPENAI_API_KEY is missing).", SETUP_STEPS)
        s = self._settings
        url = s.openai_base_url.rstrip("/") + path
        headers = {"Authorization": f"Bearer {s.openai_api_key}"}
        try:
            with httpx.Client(timeout=s.ai_timeout_seconds, transport=self._transport) as client:
                response = client.post(url, headers=headers, **kwargs)
        except httpx.TimeoutException as exc:
            record_failure(self.engine, "timeout")
            raise ModelRequestError(self.engine, "The image service took too long to answer. Try again.", retryable=True) from exc
        except httpx.TransportError as exc:
            record_failure(self.engine, "network error")
            raise ModelRequestError(self.engine, "Could not reach the image service (network error).", retryable=True) from exc

        if response.status_code >= 400:
            detail = ""
            try:
                detail = str(response.json().get("error", {}).get("message", ""))[:200]
            except ValueError:
                pass
            message, retry = explain_http_status(response.status_code, detail)
            log.warning("OpenAI images call failed with HTTP %s", response.status_code)  # no key / prompt in logs
            record_failure(self.engine, f"HTTP {response.status_code}")
            raise ModelRequestError(self.engine, message, status=response.status_code, retryable=retry)
        try:
            b64 = response.json()["data"][0]["b64_json"]
            raw = base64.b64decode(b64, validate=True)
            png = normalize_to_png(raw, max_pixels=s.max_image_pixels, max_side=s.stored_image_max_side)
        except (KeyError, IndexError, TypeError, ValueError, binascii.Error, ImageValidationError) as exc:
            record_failure(self.engine, "unusable response")
            raise ModelOutputError(self.engine, "The service answered, but the result was not a usable image.") from exc
        _reject_blank(self.engine, png)
        self.validate_image(png)
        record_success(self.engine)
        return png

    def generate(self, request: GenerationRequest) -> ModelOutput:
        prompt, negative = build_generation_prompt(request.attributes, request.additional_details)
        prompt = f"{prompt} Avoid: {negative}."
        s = self._settings
        png = self._post(
            "/images/generations",
            json={"model": s.openai_image_model, "prompt": prompt, "size": "1024x1024", "n": 1, "quality": s.openai_image_quality},
        )
        return ModelOutput(
            png=png, engine=self.engine, is_ai_generated=True, model_name=s.openai_image_model, prompt_used=prompt,
            params={"quality": s.openai_image_quality}, notes=["Generated by an AI model through the OpenAI Images API. Review the result by eye."],
        )

    def edit(self, request: EditRequest) -> ModelOutput:
        prompt = build_edit_prompt(request.instruction, request.change_summary_en, request.new_attributes, request.additional_details)
        s = self._settings
        png = self._post(
            "/images/edits",
            data={"model": s.openai_image_model, "prompt": prompt, "size": "1024x1024", "n": "1", "quality": s.openai_image_quality},
            files={"image": ("sketch.png", request.base_png, "image/png")},
        )
        notes = ["Edited by an AI model through the OpenAI Images API. Review the result by eye."]
        if request.instruction_language != "en":
            notes.append("The instruction was not in English; understanding of Hindi / Kannada text has not been tested.")
        return ModelOutput(
            png=png, engine=self.engine, is_ai_generated=True, model_name=s.openai_image_model, prompt_used=prompt,
            params={"quality": s.openai_image_quality}, notes=notes,
        )
