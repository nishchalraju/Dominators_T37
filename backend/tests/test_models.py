"""Sketch-engine adapters.

The Hugging Face and OpenAI adapters are exercised with STAND-IN clients / transports that exist only in
this test file. Nothing here proves the live services work - see docs/MODEL_SELECTION.md.
"""

import base64
import io
import json

import httpx
import pytest
from PIL import Image

from app.core.config import Settings
from app.services.sketch_models import (
    EditRequest,
    GenerationRequest,
    ModelOutputError,
    ModelRequestError,
    ModelUnavailableError,
    all_statuses,
    get_model,
    resolve_ai_engine,
)
from app.services.sketch_models.huggingface import HuggingFaceModel
from app.services.sketch_models.openai_images import OpenAIImagesModel
from app.services.sketch_models.schematic_renderer import render_schematic

ATTRS = {"face_shape": "round", "glasses": "glasses"}
SECRET = "hf_THIS_IS_A_SECRET_TOKEN_123"


def settings(**kw) -> Settings:
    return Settings(_env_file=None, hf_token=kw.pop("hf_token", ""), openai_api_key=kw.pop("openai_api_key", ""), **kw)


def sketch_png() -> bytes:
    return render_schematic(ATTRS).png


def photo_like_image() -> Image.Image:
    return Image.open(io.BytesIO(sketch_png()))


# ----------------------------------------------------------------------------- status / registry
def test_unconfigured_ai_engines_say_setup_required_and_refuse_to_run(env):
    by_engine = {s.engine: s for s in all_statuses()}
    assert by_engine["schematic"].state == "ready" and not by_engine["schematic"].is_ai
    for name in ("huggingface", "openai", "diffusers"):
        assert by_engine[name].state == "setup_required" and by_engine[name].is_ai and not by_engine[name].verified
    assert by_engine["huggingface"].setup_steps
    with pytest.raises(ModelUnavailableError) as info:
        resolve_ai_engine().generate(GenerationRequest(attributes=ATTRS))
    assert info.value.setup_steps and "HF_TOKEN" in info.value.user_message


def test_ai_provider_none_switches_ai_off(env, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "none")
    from app.core.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ModelUnavailableError):
        resolve_ai_engine()


def test_auto_selects_the_first_configured_engine(env, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from app.core.config import get_settings
    from app.services.sketch_models.registry import reset_registry

    get_settings.cache_clear()
    reset_registry()
    assert resolve_ai_engine().engine == "openai"


def test_schematic_engine_is_labelled_not_ai():
    out = get_model("schematic").generate(GenerationRequest(attributes=ATTRS))
    assert out.is_ai_generated is False and out.engine == "schematic" and out.prompt_used is None
    assert any("not AI" in n for n in out.notes)


# ----------------------------------------------------------------------------- Hugging Face (stand-in client)
class FakeClient:
    def __init__(self, image=None, error=None):
        self.image, self.error, self.calls = image, error, []

    def text_to_image(self, prompt, **kwargs):
        self.calls.append(("t2i", prompt, kwargs))
        if self.error:
            raise self.error
        return self.image

    def image_to_image(self, image, prompt=None, **kwargs):
        self.calls.append(("i2i", prompt, kwargs, image))
        if self.error:
            raise self.error
        return self.image


class HttpError(Exception):
    def __init__(self, status):
        super().__init__(f"HTTP {status} for {SECRET}")  # message deliberately contains the secret
        self.response = type("R", (), {"status_code": status})()


def hf(client, **kw):
    return HuggingFaceModel(settings(hf_token=SECRET, **kw), client_factory=lambda s: client)


def test_hf_generate_passes_prompt_and_model_and_marks_output_as_ai():
    client = FakeClient(image=photo_like_image())
    out = hf(client).generate(GenerationRequest(attributes=ATTRS, seed=7))
    kind, prompt, kwargs = client.calls[0]
    assert kind == "t2i" and "round face" in prompt and "wearing glasses" in prompt
    assert kwargs["model"] == "Qwen/Qwen-Image" and kwargs["seed"] == 7 and "negative_prompt" in kwargs
    assert out.is_ai_generated and out.engine == "huggingface" and out.model_name == "Qwen/Qwen-Image"
    assert Image.open(io.BytesIO(out.png)).format == "PNG"


def test_hf_prompt_mentions_only_specified_attributes():
    client = FakeClient(image=photo_like_image())
    hf(client).generate(GenerationRequest(attributes={"face_shape": "round"}))
    prompt = client.calls[0][1]
    assert "round face" in prompt and "glasses" not in prompt and "beard" not in prompt


def test_hf_edit_sends_the_previous_image_and_an_english_summary():
    client = FakeClient(image=photo_like_image())
    base = sketch_png()
    out = hf(client).edit(EditRequest(base_png=base, base_attributes={}, new_attributes=ATTRS, instruction="चश्मा जोड़ें",
                                      instruction_language="hi", change_summary_en="Glasses: Wearing glasses"))
    kind, prompt, kwargs, sent = client.calls[0]
    assert kind == "i2i" and sent == base and kwargs["model"] == "Qwen/Qwen-Image-Edit"
    assert "Glasses: Wearing glasses" in prompt and "चश्मा जोड़ें" in prompt
    assert any("not been tested" in n for n in out.notes)  # honest about Hindi / Kannada


@pytest.mark.parametrize("status,needle,retry", [(401, "rejected the credentials", False), (402, "credits", False), (404, "does not serve", False),
                                                 (429, "Rate limit", True), (503, "server error", True)])
def test_hf_http_errors_become_clear_messages_without_leaking_the_token(status, needle, retry):
    model = hf(FakeClient(error=HttpError(status)))
    with pytest.raises(ModelRequestError) as info:
        model.generate(GenerationRequest(attributes=ATTRS))
    assert needle in info.value.user_message and info.value.retryable is retry
    assert SECRET not in info.value.user_message and SECRET not in str(info.value)
    status_obj = model.status()
    assert status_obj.last_error and SECRET not in status_obj.last_error and not status_obj.verified


def test_hf_timeout_is_reported_as_retryable():
    with pytest.raises(ModelRequestError) as info:
        hf(FakeClient(error=httpx.ReadTimeout("slow"))).generate(GenerationRequest(attributes=ATTRS))
    assert info.value.retryable and "too long" in info.value.user_message


def test_hf_rejects_blank_and_non_image_results():
    blank = Image.new("RGB", (256, 256), (255, 255, 255))
    with pytest.raises(ModelOutputError, match="blank"):
        hf(FakeClient(image=blank)).generate(GenerationRequest(attributes=ATTRS))
    with pytest.raises(ModelOutputError):
        hf(FakeClient(image="not an image")).generate(GenerationRequest(attributes=ATTRS))


def test_hf_success_marks_the_engine_verified_but_status_never_claims_it_before():
    model = hf(FakeClient(image=photo_like_image()))
    assert model.status().state == "ready" and model.status().verified is False
    model.generate(GenerationRequest(attributes=ATTRS))
    assert model.status().verified is True


def test_hf_without_token_raises_unavailable_and_never_builds_a_client():
    called = []
    model = HuggingFaceModel(settings(), client_factory=lambda s: called.append(1))
    with pytest.raises(ModelUnavailableError):
        model.generate(GenerationRequest(attributes=ATTRS))
    assert not called


# ----------------------------------------------------------------------------- OpenAI (mock transport)
def openai_model(handler, **kw):
    return OpenAIImagesModel(settings(openai_api_key="sk-secret-key", **kw), transport=httpx.MockTransport(handler))


def b64_response(png: bytes) -> httpx.Response:
    return httpx.Response(200, json={"data": [{"b64_json": base64.b64encode(png).decode()}]})


def test_openai_generate_posts_json_with_bearer_key_and_decodes_the_image():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["auth"], seen["body"] = str(request.url), request.headers["authorization"], json.loads(request.content)
        return b64_response(sketch_png())

    out = openai_model(handler).generate(GenerationRequest(attributes=ATTRS))
    assert seen["url"].endswith("/images/generations") and seen["auth"] == "Bearer sk-secret-key"
    assert seen["body"]["model"] == "gpt-image-2.5-sunburst" and "round face" in seen["body"]["prompt"]
    assert out.is_ai_generated and out.engine == "openai"


def test_openai_edit_uses_multipart_with_the_previous_image():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["type"], seen["body"] = str(request.url), request.headers["content-type"], request.content
        return b64_response(sketch_png())

    openai_model(handler).edit(EditRequest(base_png=sketch_png(), base_attributes={}, new_attributes=ATTRS, instruction="add glasses",
                                           change_summary_en="Glasses: Wearing glasses"))
    assert seen["url"].endswith("/images/edits") and seen["type"].startswith("multipart/form-data")
    assert b'name="image"' in seen["body"] and b"Glasses: Wearing glasses" in seen["body"]


@pytest.mark.parametrize("status,needle", [(401, "credentials"), (429, "Rate limit"), (500, "server error")])
def test_openai_errors_never_leak_the_key(status, needle):
    model = openai_model(lambda r: httpx.Response(status, json={"error": {"message": "bad key sk-secret-key"}}))
    with pytest.raises(ModelRequestError) as info:
        model.generate(GenerationRequest(attributes=ATTRS))
    assert needle in info.value.user_message and "sk-secret-key" not in info.value.user_message


def test_openai_garbage_response_is_an_output_error():
    with pytest.raises(ModelOutputError):
        openai_model(lambda r: httpx.Response(200, json={"data": [{"b64_json": "###not-base64###"}]})).generate(GenerationRequest(attributes=ATTRS))
    with pytest.raises(ModelOutputError):
        openai_model(lambda r: httpx.Response(200, json={"unexpected": True})).generate(GenerationRequest(attributes=ATTRS))


def test_openai_without_key_is_unavailable():
    with pytest.raises(ModelUnavailableError):
        OpenAIImagesModel(settings()).generate(GenerationRequest(attributes=ATTRS))
