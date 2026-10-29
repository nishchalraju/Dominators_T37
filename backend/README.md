# SketchAssist AI - backend

FastAPI + SQLAlchemy + SQLite. Serves the JSON API under `/api` and, when the frontend has been built (`npm run build` in the
project root), the web app for every other URL.

## Set up and run (Windows PowerShell; on macOS / Linux use `python3` and `source .venv/bin/activate`)

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

Needs Python 3.11+ (developed on 3.13). The database file is created in `backend/storage/` on first start. Stop with *Ctrl+C*.
Interactive docs: <http://localhost:8000/docs> (Swagger UI) and <http://localhost:8000/redoc>. Health check: `GET /api/health`.

## Configuration (`backend/.env`, copied from `.env.example`)

Everything that varies between machines is an environment variable. **Never commit `.env`; never put these values in frontend code.**

| Variable | Default | Meaning |
|---|---|---|
| `APP_ENV` | `development` | `production` makes a missing `SECRET_KEY` an error |
| `SECRET_KEY` | auto-created in dev (`storage/.secret_key`) | signs login tokens; **required in production** (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | login lifetime |
| `CORS_ORIGINS` | `http://localhost:5173,...` | browsers allowed to call the API from another origin |
| `ALLOW_REGISTRATION` | `true` | set `false` once your accounts exist |
| `FRAME_ANCESTORS` | empty | e.g. `'none'` in production to forbid embedding the app in other sites |
| `DATABASE_URL`, `STORAGE_DIR`, `DATASETS_DIR`, `FRONTEND_DIST_DIR` | inside the project | change locations |
| `AI_PROVIDER` | `auto` | `auto` / `none` / `huggingface` / `openai` / `diffusers` |
| `HF_TOKEN`, `HF_PROVIDER`, `HF_T2I_MODEL`, `HF_EDIT_MODEL` | empty / `auto` / `Qwen/Qwen-Image` / `Qwen/Qwen-Image-Edit` | Hugging Face Inference Providers |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_IMAGE_MODEL`, `OPENAI_IMAGE_QUALITY` | empty / OpenAI / `gpt-image-2.5-sunburst` / `medium` | OpenAI Images API (names change - check OpenAI's docs) |
| `LOCAL_T2I_MODEL`, `LOCAL_EDIT_MODEL`, `LOCAL_DEVICE`, `LOCAL_STEPS` | FLUX.1-schnell / Qwen-Image-Edit / `auto` / `4` | experimental local inference (`pip install -r requirements-ai-local.txt`, big GPU) |

With no AI settings the app still works: the rule-based **schematic** engine is always available and AI engines report "setup required".

## Folder layout

```
app/
  api/        routers: auth, meta, dashboard, cases, descriptions, sketches, datasets (+evaluations), reports; deps.py
  core/       config.py, database.py, security.py, errors.py, logging.py
  models/     User, Case, WitnessDescription, SketchVersion, InvestigatorNote, DatasetRecord/Inspection, ModelEvaluation, ActivityLog
  schemas/    Pydantic request / response models
  services/   attributes (vocabulary), description_parser/, sketch_models/, sketch_workflow, storage, image_tools, report,
              datasets, custom_dataset, evaluation, cases, activity, provenance, disclaimers
  assets/fonts/   Noto fonts (OFL) for PDF text in Latin, Devanagari and Kannada
  main.py     create_app(): error handlers, security headers, CORS, router, static frontend
datasets/{external,custom,processed,metadata}   see docs/DATASETS.md
scripts/      command-line tools (below)
tests/        pytest suite (synthetic data only)
```

## Scripts (run from `backend`, venv active)

| Command | What it does |
|---|---|
| `python scripts/init_db.py` | create tables (safe to repeat); `--reset --yes` wipes everything |
| `python scripts/create_user.py --username alice --admin` | create / promote a user without the web form (asks for the password) |
| `python scripts/validate_custom_dataset.py [file.csv]` | validate a custom attribute CSV; exit code 1 + named problems if invalid |
| `python scripts/inspect_datasets.py [--dataset cufs]` | inventory the dataset folders into the database |
| `python scripts/evaluate_parser.py --split dev\|test\|all [--only-reviewed] [--save]` | measure the description parser |
| `python scripts/generate_dataset_schema.py [--check]` | (re)write the JSON Schema from the vocabulary |
| `python scripts/export_dataset_cards.py` | write `datasets/metadata/external_datasets.json` |
| `python scripts/generate_api_docs.py [--check]` | write `docs/API.md` and `docs/openapi.json` from the code |

## API overview (full reference: `docs/API.md`, live at `/docs`)

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Cases | `GET/POST /api/cases`, `GET/PATCH/DELETE /api/cases/{case_id}`, `GET/POST /api/cases/{case_id}/notes` |
| Descriptions | `POST /api/descriptions/parse`, `GET/POST /api/cases/{case_id}/descriptions`, `PUT /api/cases/{case_id}/descriptions/{id}` |
| Sketches | `POST /api/sketches/generate`, `POST /api/sketches/{id}/revise`, `GET /api/sketch-versions?case_id=`, `GET /api/sketch-versions/{id}[/image\|/thumbnail]`, `POST /api/sketch-versions/{id}/select`, `GET /api/engines` |
| Datasets / evaluation | `GET /api/datasets/status`, `POST /api/datasets/inspect` (admin), `GET /api/evaluations`, `POST /api/evaluations` (admin) |
| Reports / dashboard | `GET /api/cases/{case_id}/report` (PDF), `GET /api/dashboard`, `GET /api/activity` |
| Meta | `GET /api/meta/attributes` (vocabulary, no sign-in), `GET /api/health` |

Errors always look like `{"detail": "...", "code": "machine_code"}`; validation errors (422) add `fields`; AI-engine problems add
`engine` and `setup_steps`; an unsupported revision lists what was `ignored`.

## Tests

```powershell
python -m pytest            # 298 tests, about 40 s
```

Covers: vocabulary (incl. skin colour), the multilingual parser (same canonical values in EN / HI / KN, negation, unrecognised phrases, conflicts, ages,
regressions), the instruction interpreter, the renderer (every value of every attribute changes the picture; deterministic
output), engine adapters (stand-in clients), authentication and authorisation, cases / notes / descriptions / sketches / versions,
PDF content, datasets / validator / evaluation, upgrading a database made before the name columns existed, image and storage security, security headers, static serving, and that the
generated docs are not stale. Stand-in model clients exist **only in the tests**.

## Notes for production use (this is a prototype)

Set `APP_ENV=production` and a real `SECRET_KEY`, run behind HTTPS (a reverse proxy), set `CORS_ORIGINS` and `FRAME_ANCESTORS`,
back up `storage/`, and consider PostgreSQL and a migration tool (the project creates tables with `create_all` and has **no migrations**:
after changing a model, recreate the database or migrate by hand). Logout is client-side (stateless token) and login / rate
limits are kept in memory per process - see [../docs/STATUS.md](../docs/STATUS.md).
