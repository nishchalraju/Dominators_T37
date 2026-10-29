# Architecture

SketchAssist AI 3.0 is a single-page web app (React + TypeScript) talking JSON over HTTP to a FastAPI backend that stores
data in SQLite and sketch images as PNG files. In production one process serves both: the API under `/api` and the built
frontend for every other URL.

```
 Browser (React SPA)                                   Server (FastAPI, one process)
 ───────────────────                                   ─────────────────────────────────────────────
 pages ── hooks ── services/http ──  /api/*  ───────►  api (routers) ──► schemas (Pydantic validation)
   │         │      Bearer token                              │
 providers   └─ AuthImage (images fetched with the token)     ▼
 (auth, vocabulary,                                    services ─┬─ description_parser  (EN / HI / KN, rule based)
  active case, toasts)                                           ├─ sketch_models       (engines + registry)
                                                                 ├─ sketch_workflow     (generate / revise / select)
                                                                 ├─ report              (PDF)    datasets / evaluation
                                                                 ▼
                                                        models (SQLAlchemy) ──► SQLite       storage/sketches/<case>/<uuid>.png
```

## Backend layout (`backend/app`)

| Folder | Purpose |
|---|---|
| `core/` | settings (env vars), database engine, password hashing + JWT + throttles, error format, logging |
| `models/` | SQLAlchemy tables (see below) |
| `schemas/` | Pydantic request / response models. They are the API contract and the source of `docs/API.md` |
| `services/` | all business logic (kept out of the routers so it can be tested without HTTP) |
| `api/` | thin FastAPI routers + dependencies (current user, admin check, rate limit) |
| `main.py` | app factory: error handlers, security headers, CORS, router, static frontend |
| `assets/fonts/` | Noto Sans / Devanagari / Kannada (SIL OFL) so PDFs print Hindi and Kannada correctly |

### Services worth knowing

* `attributes.py` - the **controlled vocabulary** (12 attributes and their allowed values; version 1.1 added `skin_colour`). Single
  source of truth: the parser, the schematic renderer, prompt builder, dataset validator, JSON schema **and the web forms**
  (`GET /api/meta/attributes`) all read it, so a value the UI offers can never be rejected by the server. An attribute can carry
  colour chips (`swatches`): the web UI shows the chip next to the dropdown and the renderer paints exactly that colour.
* `description_parser/` - tokenizer that understands Indic combining marks, one word list per language (`lexicon_en/hi/kn.py`,
  plain data a student can read), matching rules (`rules.py`), age expressions (`age.py`) and the instruction interpreter
  (`revision.py`). See [EVALUATION.md](EVALUATION.md).
* `sketch_models/` - the engine interface (`base.py`), the rule-based `schematic` engine (`schematic_renderer.py`), adapters for
  Hugging Face / OpenAI / local diffusers, `registry.py` (which engine answers a request) and `prompts.py`. The renderer carries a
  *skin palette* (skin, shade, lips, fine lines) through every part it draws, so one choice recolours face, neck and ears consistently;
  colour never changes the random seed, so "make the skin darker" moves no stroke. With no skin colour chosen it draws the original
  neutral tone, byte for byte as before. `prompts.py` asks AI engines for a colour-pencil sketch only when a skin colour was chosen.
* `sketch_workflow.py` - creates versions. It enforces: append-only versions, no silent engine fallback, closed cases are read-only.
* `report.py` - the PDF (fpdf2 + text shaping).
* `custom_dataset.py`, `datasets.py`, `evaluation.py` - dataset validation / inspection and parser metrics.

## Data model

| Table | Holds | Notes |
|---|---|---|
| `users` | username, **scrypt password hash**, role (`admin` / `investigator`), responsible-use acknowledgement time | first registered user is admin |
| `cases` | public case ID `SA-<year>-<6 chars>`, title, incident date, reference, **investigator name, witness name**, status, owner | ID is unique (constraint + retry). The two names are personal data: not written to the activity log, searchable only by the owner or an administrator, `""` = not recorded (older cases) |
| `witness_descriptions` | **original text (never edited)**, language, parser output, reviewer-confirmed attributes, unrecognised phrases, parser version | |
| `sketch_versions` | version number, parent, kind, instruction, attribute snapshot, **engine + `is_ai_generated` + model name**, prompt used, notes, image path + SHA-256 | `UNIQUE(case, version_number)`; partial unique index = at most one selected version per case; rows are only ever inserted |
| `investigator_notes` | append-only notes | no update / delete endpoint exists |
| `dataset_records`, `dataset_inspections` | the inventory found by the last inspection | empty until a real inspection ran |
| `model_evaluations` | one row per real evaluation run (n, metrics, data hash, parser version) | nothing is seeded |
| `activity_logs` | audit trail (the dashboard's "recent activity") | keeps the case reference after a case is deleted |

## Main flows

* **Generate** `POST /api/sketches/generate` -> authorise case -> choose engine (`schematic` or the configured AI engine; an
  unconfigured AI engine answers **503 with setup steps** - never a substitute) -> engine returns PNG -> image is validated
  and written to a new random file name -> new `sketch_versions` row, selected -> activity log.
* **Revise** `POST /api/sketches/{id}/revise` -> `interpret_revision` turns the sentence into attribute changes (or lists what it
  could not do) -> engine draws a **new** version from the changed attributes (schematic) or edits the previous image (AI) ->
  new row with `parent_id`. The parent row and file are untouched.
* **Image requests** need the Authorization header, so the browser fetches them as blobs (`AuthImage`). The server compares the
  file's SHA-256 with the stored value before serving it (tamper / corruption check). Downloads add a caption band
  ("SCHEMATIC COMPOSITE - NOT AI-GENERATED" / "AI-GENERATED IMAGE") - the stored file itself stays clean.
* **Report** `GET /api/cases/{id}/report` -> PDF with metadata, witness text, attributes, selected sketch with provenance caption,
  version history with instructions, notes, methods and limitations, generation time, disclaimers.

## Frontend layout (`src`)

`components/` (UI primitives in `ui/`, domain components, `providers/`), `pages/` (one per section), `layouts/` (app shell,
auth layout), `services/` (`http.ts` fetch wrapper, `api.ts` typed endpoint functions, `storage.ts`), `hooks/`
(`useAsync`, contexts and their hooks), `types/api.ts` (mirrors the backend schemas), `utils/`.

State is deliberately simple: server data is loaded with the small `useAsync` hook; four React contexts hold what is truly
global - the signed-in user, the vocabulary, the **active case** (remembered across pages and reloads) and toasts. There is no
state library.

## Security and privacy design

| Concern | What is done |
|---|---|
| Passwords | scrypt (N=2^15) with a random salt; never stored or logged in plain text; minimum 10 characters; constant-time comparison; unknown users cost the same time as wrong passwords |
| Sessions | signed JWT (HS256) with an expiry; sent as `Authorization: Bearer`, not a cookie, so there is no CSRF surface. `SECRET_KEY` comes from the environment (auto-generated in development, **required** in production) |
| Brute force | failed logins are throttled per client + username (in memory); sketch generation is rate-limited per user (protects paid AI calls) |
| Authorisation | every case, description, note, sketch and report check owner-or-admin. A case that is not yours looks identical to one that does not exist (404). Admin-only: dataset inspection, evaluation runs |
| Input validation | Pydantic schemas reject unknown fields, over-long text and values outside the vocabulary; ID formats, dates and lengths are checked |
| Files | images are re-encoded to clean PNG (metadata stripped), size / pixel limits, random server-chosen names, path-traversal guard in `storage.py`, hash check on read |
| Browser | CSP on the app page (`default-src 'self'`, no inline scripts, `object-src 'none'`), `nosniff`, `no-referrer`, **`Permissions-Policy` denies camera, microphone, geolocation and payment**. `FRAME_ANCESTORS` can forbid embedding |
| Secrets | API keys live only in `backend/.env` / the environment, never in frontend code; tokens and keys are never written to logs; error messages shown to users do not contain them (tested) |
| Privacy | no photos are processed; witness text is not logged; activity-log summaries never contain witness text |

Known gaps are listed honestly in [STATUS.md](STATUS.md) (stateless logout, in-memory throttles, no HTTPS termination, ...).

## Why these choices (short version)

* **Rule-based parser, not a neural model.** No labelled multilingual witness data exists here, and a rule-based parser is
  inspectable: every value comes with the words that caused it and everything not understood is listed. The cost is limited coverage.
* **A separate, clearly labelled schematic engine.** Without GPU or credentials no AI model can run in this environment. A
  rule-based drawing makes generate / revise / compare / report testable offline - and is labelled "not AI" in the UI, the
  database, downloads and the PDF so it can never be mistaken for AI output.
* **No silent fallback.** If an AI engine fails or is not set up the user gets the reason; falling back would pass non-AI output
  off as AI output.
* **Append-only versions and notes.** The evidence trail must not change after the fact.
* **SQLite + SQLAlchemy.** Zero setup for students; the ORM keeps a move to PostgreSQL a configuration change (`DATABASE_URL`).
