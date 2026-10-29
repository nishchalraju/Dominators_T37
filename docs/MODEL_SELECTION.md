# Choosing the sketch-generation engine

This document records **what was found, what was decided and what could not be verified**. Facts were checked in October 2026
from the sources named below; model names and terms change, so re-check before relying on them.

## Constraints of the build environment

No GPU, 1.9 GB of RAM, no API credentials. Therefore **no AI model was run end to end**. The Hugging Face and OpenAI adapters
are implemented against the documented APIs and unit-tested with stand-in clients / transports (which exist only in the test
files). They have **not** been called against the live services. This is the single most important limitation of the AI path.

## Requirements used to compare models

Text-to-image **and** image editing (so a revision can modify the previous sketch), a licence that does not forbid
law-enforcement use, availability without special approval, hosted option (no GPU needed), realistic for a student project.

## Findings

| Model / service | Licence finding | Verdict |
|---|---|---|
| **Qwen/Qwen-Image** (text-to-image) | Apache-2.0; not gated; served on Hugging Face Inference Providers (fal-ai, replicate, wavespeed) | **default generator** |
| **Qwen/Qwen-Image-Edit** (editing) | Apache-2.0; not gated; same providers (newer -2509 / -2511 variants exist on fal-ai, wavespeed) | **default editor** |
| FLUX.1 [schnell] | Apache-2.0 but gated ("accept the conditions"); text-to-image only | usable for the optional local adapter |
| FLUX.1 Kontext [dev], FLUX.1 Krea [dev] | FLUX [dev] Non-Commercial License v1.1.1 **forbids** commercial, military, **surveillance (including research)** and **biometric processing** uses | rejected |
| Stable Diffusion 1.x / 2.x and derivatives (e.g. InstructPix2Pix) | CreativeML OpenRAIL-M, Attachment A prohibits generating information "for administration of justice, law enforcement, immigration or asylum processes" | rejected as a default: licence risk for a forensic tool |
| OpenAI Images API (`gpt-image-2.5-sunburst`, `gpt-image-2.5-flare` at the time of writing) | commercial service under OpenAI's usage policies; may require organisation verification; names change often | **alternative adapter**, model name configurable (`OPENAI_IMAGE_MODEL`) |
| Local `diffusers` | depends on the chosen model; needs a large GPU | **optional adapter, experimental, untested** |

Sources read: Hugging Face model cards and the Hub API (licence, gating, provider mappings), the Hugging Face `huggingface_hub`
inference documentation (`text_to_image`, `image_to_image`), the CreativeML OpenRAIL-M licence text, the Black Forest Labs
FLUX [dev] licence text, and OpenAI's image-generation guide and API reference.

## Decision

1. `AI_PROVIDER=auto` (default) uses the first **configured** hosted engine: Hugging Face (`HF_TOKEN`) with Qwen-Image /
   Qwen-Image-Edit, otherwise OpenAI (`OPENAI_API_KEY`). `diffusers` only when selected explicitly.
2. If none is configured the AI engine reports **"setup required"** with concrete steps; requests answer **503**. There is no
   fallback to another engine.
3. A separate **schematic engine** (Pillow drawing driven by the attributes) is always available. It is *not AI*, is labelled so
   everywhere, and is the only engine that was exercised end to end here.

## How the adapters behave (and are tested)

* One interface (`sketch_models/base.py`): `status()`, `generate()`, `edit()`, `validate_image()`; three error types
  (`ModelUnavailableError` = setup required, `ModelRequestError` = provider failed, `ModelOutputError` = unusable image).
* HTTP 401/403, 402, 404, 429, 5xx and timeouts become clear messages; blank or non-image results are rejected; **tokens and keys
  never appear in messages or logs**.
* `GET /api/engines` reports `state` (`ready` / `setup_required`), `verified` (true only after a real request has succeeded since
  the server started) and `last_evaluated_at` (null = never evaluated).
* Prompts describe only attributes the investigator specified; unspecified features are left to the model (the UI says AI
  engines may invent details). A revision sends the previous image, an English summary of the recognised changes and the original
  instruction. **Hindi / Kannada instructions are passed along but understanding of them by the models has not been tested.**
* **Skin colour and the AI engines (untested with a real model).** The default prompt asks for a *black-and-white* graphite sketch. When the
  investigator chose a skin colour, a black-and-white drawing cannot show it, so the prompt asks for a soft *colour-pencil* sketch instead and names the colour
  ("white (fair, light) skin", "brown (wheatish, medium) skin", "black (dark) skin"); a revision that changes it tells the model to recolour the face, ears
  and neck and leave hair, eyes and clothes alone. Whether a given model follows this - or recolours more than it should - has **not** been tested
  (no credentials were available); check every AI sketch against the chosen colour. The prompt wording is covered by unit tests only.
* AI output is stored with `is_ai_generated = true`, the model name, the prompt used and notes, and is captioned
  "AI-GENERATED IMAGE - REQUIRES HUMAN REVIEW" on downloads and in the PDF.

## To switch an AI engine on (needs your own credentials)

1. Create a fine-grained Hugging Face token that may call Inference Providers; put `HF_TOKEN=...` in `backend/.env`; restart.
2. Open **Dataset and AI Evaluation**: the engine should show "Ready". It shows "Confirmed working" only after a first successful sketch.
3. Generate a sketch with the AI engine. Provider usage is billed to / limited by your account. Changing the model IDs? Read the
   new model's licence first (see the table above).

## No quality evaluation of sketch generation exists

The project has no benchmark pairing witness descriptions with ground-truth sketches, and the published datasets pair *photos*
with *sketches* (see [DATASETS.md](DATASETS.md)). The page therefore shows "Never evaluated" for every engine and claims no quality figure.
