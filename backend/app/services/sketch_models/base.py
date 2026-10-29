"""The interface every sketch engine implements.

An *engine* turns attributes (and, for revisions, an instruction + the previous image)
into a PNG. There are two kinds:

* ``schematic`` - a rule-based drawing (NOT artificial intelligence). Always available.
* AI engines (``huggingface``, ``openai``, ``diffusers``) - need credentials or hardware.
  When they are not set up they say so and refuse to run; there is NEVER a silent
  fallback to another engine, because that would pass non-AI output off as AI output.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.config import get_settings
from app.services.attributes import Attributes
from app.services.image_tools import ImageInfo, ImageValidationError, inspect_image


# --------------------------------------------------------------------------- errors
class ModelError(Exception):
    """Base class for engine errors. ``user_message`` is safe to show in the UI."""

    code = "model_error"

    def __init__(self, engine: str, user_message: str, *, status: int | None = None, retryable: bool = False):
        super().__init__(user_message)
        self.engine = engine
        self.user_message = user_message
        self.status = status
        self.retryable = retryable


class ModelUnavailableError(ModelError):
    """The engine is not configured / installed ("setup required")."""

    code = "model_unavailable"

    def __init__(self, engine: str, user_message: str, setup_steps: list[str] | None = None):
        super().__init__(engine, user_message)
        self.setup_steps = setup_steps or []


class ModelRequestError(ModelError):
    """The engine was reached but the request failed (bad credentials, quota, timeout ...)."""

    code = "model_request_failed"


class ModelOutputError(ModelError):
    """The engine answered, but the answer is not a usable image."""

    code = "model_output_invalid"


# --------------------------------------------------------------------------- data classes
@dataclass
class GenerationRequest:
    attributes: Attributes
    additional_details: str = ""
    seed: int | None = None


@dataclass
class EditRequest:
    base_png: bytes
    base_attributes: Attributes
    new_attributes: Attributes
    instruction: str  # exactly what the investigator typed
    instruction_language: str = "en"
    change_summary_en: str = ""  # structured, English description of the detected changes
    additional_details: str = ""


@dataclass
class ModelOutput:
    png: bytes
    engine: str
    is_ai_generated: bool
    model_name: str | None
    prompt_used: str | None = None
    params: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class ModelStatus:
    engine: str
    label: str
    is_ai: bool
    state: str  # ready | setup_required | disabled
    detail: str
    setup_steps: list[str] = field(default_factory=list)
    supports_generate: bool = True
    supports_edit: bool = True
    models: dict[str, str] = field(default_factory=dict)
    licence_note: str | None = None
    verified: bool = False  # True only after a real call succeeded since the server started
    last_success_at: datetime | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None

    @property
    def available(self) -> bool:
        return self.state == "ready"


# --------------------------------------------------------------------------- health tracking
_health_lock = threading.Lock()
_health: dict[str, dict] = {}


def record_success(engine: str) -> None:
    with _health_lock:
        _health.setdefault(engine, {}).update(last_success_at=datetime.now(timezone.utc))


def record_failure(engine: str, message: str) -> None:
    with _health_lock:
        _health.setdefault(engine, {}).update(last_error=message[:300], last_error_at=datetime.now(timezone.utc))


def apply_health(status: ModelStatus) -> ModelStatus:
    with _health_lock:
        info = dict(_health.get(status.engine, {}))
    status.last_success_at = info.get("last_success_at")
    status.last_error = info.get("last_error")
    status.last_error_at = info.get("last_error_at")
    status.verified = status.last_success_at is not None
    return status


def reset_health() -> None:
    """Forget recorded successes / failures (used by tests)."""
    with _health_lock:
        _health.clear()


# --------------------------------------------------------------------------- the interface
class SketchModel(ABC):
    engine: str
    label: str
    is_ai: bool

    @abstractmethod
    def status(self) -> ModelStatus:
        """Describe whether this engine can run right now (without making a paid request)."""

    @abstractmethod
    def generate(self, request: GenerationRequest) -> ModelOutput:
        """Create a first sketch from attributes."""

    @abstractmethod
    def edit(self, request: EditRequest) -> ModelOutput:
        """Create a revised sketch from the previous image and an instruction."""

    def validate_image(self, data: bytes) -> ImageInfo:
        """Reject output that is not a real, reasonably sized image."""
        try:
            return inspect_image(data, max_pixels=get_settings().max_image_pixels)
        except ImageValidationError as exc:
            raise ModelOutputError(self.engine, f"The engine returned an unusable image: {exc}") from exc
