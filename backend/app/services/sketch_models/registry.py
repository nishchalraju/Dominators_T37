"""Chooses which engine handles a request. There is no silent fallback between engines."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.services.sketch_models.base import ModelStatus, ModelUnavailableError, SketchModel
from app.services.sketch_models.diffusers_local import DiffusersLocalModel
from app.services.sketch_models.huggingface import HuggingFaceModel
from app.services.sketch_models.openai_images import OpenAIImagesModel
from app.services.sketch_models.schematic import SchematicModel

ENGINES = ("schematic", "huggingface", "openai", "diffusers")
AI_ENGINES = ("huggingface", "openai", "diffusers")
ENGINE_LABELS = {
    "schematic": "Schematic composite (rule-based, not AI)",
    "huggingface": "Hugging Face Inference Providers (AI)",
    "openai": "OpenAI Images API (AI)",
    "diffusers": "Local diffusers model (AI, experimental)",
}

_instances: dict[str, SketchModel] = {}


def _build(engine: str, settings: Settings) -> SketchModel:
    if engine == "schematic":
        return SchematicModel()
    if engine == "huggingface":
        return HuggingFaceModel(settings)
    if engine == "openai":
        return OpenAIImagesModel(settings)
    return DiffusersLocalModel(settings)


def get_model(engine: str) -> SketchModel:
    if engine not in ENGINES:
        raise KeyError(engine)
    if engine not in _instances:
        _instances[engine] = _build(engine, get_settings())
    return _instances[engine]


def reset_registry() -> None:
    """Drop cached adapters (tests change settings between runs)."""
    _instances.clear()


def resolve_ai_engine() -> SketchModel:
    """The AI engine selected by AI_PROVIDER. With 'auto' the first *configured* one is used.

    If none is configured this still returns the Hugging Face adapter, whose ``generate`` raises
    ``ModelUnavailableError`` with setup steps - the caller must show that, never substitute another engine.
    """
    provider = get_settings().ai_provider
    if provider == "none":
        raise ModelUnavailableError("none", "AI engines are switched off (AI_PROVIDER=none).", ["Set AI_PROVIDER=auto in backend/.env."])
    if provider != "auto":
        return get_model(provider)
    for name in ("huggingface", "openai"):
        model = get_model(name)
        if model.status().available:
            return model
    return get_model("huggingface")


def all_statuses() -> list[ModelStatus]:
    return [get_model(name).status() for name in ENGINES]
