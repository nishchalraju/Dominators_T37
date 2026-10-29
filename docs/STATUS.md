# Status: what is done, what is not, and how it was checked

Version 3.0.0 · academic prototype · last full verification run 29 Oct 2026 (after adding skin colour and the investigator / witness names).
The project was built from an empty folder (there was no earlier code to preserve), so every file was new; the later additions
are described in section 2.

## 1. Test results (latest full run)

| Check | Result |
|---|---|
| Backend `python -m pytest` | **298 passed** (~38 s) |
| Frontend `npm test` (Vitest + Testing Library, 17 files) | **119 passed** |
| `npm run typecheck` (TypeScript 7, strict) | clean |
| `npm run lint` (oxlint) | 0 warnings, 0 errors |
| `npm run build` | OK - 403.8 KB JavaScript (118.9 KB gzip), 29.0 KB CSS |
| End-to-end, real Chromium against the real server (`e2e/investigator-flow.spec.ts`) | **14 / 14 passed** on a fresh database (run twice) |
| Accessibility, axe-core WCAG 2.0 / 2.1 A + AA on every page and main state (`e2e/accessibility.spec.ts`) | **8 / 8 scans, zero violations** (at any impact level) |
| Parser evaluation (parser 1.2.0, synthetic data, see [EVALUATION.md](EVALUATION.md)) | 87/90 exact (96.7 %); dev 48/51; test 39/39 **but no longer a clean holdout** (clean first run of the original test split: 28/30 = 93.3 %); skin colour 18/18, **not a blind test** |

What the tests prove, in plain words: every attribute value visibly changes the sketch; a revision produces different pixels and leaves the
earlier version byte-for-byte unchanged; the same face described in English, Hindi or Kannada yields the same attributes; unrecognised phrases are
listed; another user cannot read your case or images; an unconfigured AI engine answers "setup required" and nothing is created; the PDF
contains the required sections and prints Hindi and Kannada; datasets that are not installed show zero.
Added with the skin colour and the names: the face is painted in exactly the colour chip the editor shows (checked on the real pixels, in a real
browser too); changing only the colour moves no stroke; a drawing without a skin colour is byte-for-byte what it was before; the colour of hair, clothes
and masks is never read as a skin colour; names in English, Hindi and Kannada are stored, searched, shown and printed; a database made before the names
existed is upgraded on start-up without losing a row.

Bugs that the tests found *and that were fixed* during the build: the age expression "35 years **old**" was cancelled by the word "old"; a
self-intersecting hair and beard polygon; `ಧರಿಸುವುದಿಲ್ಲ` ("does not wear") read as positive; a lost confirmation banner after a revision;
inline links distinguished by colour only (WCAG 1.4.1); "1 attribute differ"; accessible names missing a space ("Compareversion 1");
an orphaned PDF heading; raw attribute keys in a note; the unit-test mock hiding a remount bug; and, with the names, an investigator name suggested from
an account name containing `_` that the server then refused (found by the accessibility end-to-end run; the server now accepts `_`, and the form only
suggests a name that has letters).

**Not tested (be aware):** any live AI service (no credentials were available); Windows (commands follow the standard PowerShell flow but
were verified on Linux); browsers other than Chromium; screen readers or other manual accessibility testing (automated tools find only part of the problems);
load / performance; PostgreSQL.

## 2. Completed features (against the specification)

| Requirement | Where / how |
|---|---|
| React + TypeScript + Vite, Tailwind, lucide-react, React Router; FastAPI, Pydantic, SQLite + SQLAlchemy, Pillow, PDF | the whole project |
| Required folder structure (`src/{components,pages,layouts,services,hooks,types,utils}`, `backend/{app/{api,models,schemas,services,core},datasets/{external,custom,processed,metadata},scripts,tests,...}`) | yes |
| Navigation: Dashboard, New Investigation, Case Management, Sketch Workspace, Dataset and AI Evaluation, Reports, Settings; selected case persists | `layouts/AppShell`, `ActiveCaseProvider` (survives reloads, cleared on sign-out) |
| Dashboard: stats from the DB, searchable case table, recent activity from stored records, no fake data | `GET /api/dashboard`, `/api/cases?q=`, audit log |
| Cases: auto-generated unique ID, validation, reopen | `SA-<year>-<6 chars>` with unique constraint + retry; closed cases read-only until reopened |
| Multilingual (EN / KN / HI) parser: editable estimates, unrecognised phrases surfaced, original text preserved, same canonical values across languages | `services/description_parser`, `DescriptionForm`, `ParseResultPanel` |
| Facial attribute editor; instruction-based revisions that really change the image | `AttributeEditor`, `revision.py`, schematic renderer (test: every value of every attribute changes pixels) |
| **Skin colour** (white / brown / black): pick it, read it from English / Hindi / Kannada text, change it by instruction ("make the skin brown", "darker"), see it drawn, send it to AI prompts, print it | `attributes.py` (vocabulary 1.1), lexicons, `revision.py`, `schematic_renderer.py`, `prompts.py`, PDF; colour chips in `AttributeEditor` |
| **Investigator name and witness name** on every case: asked when a case is opened, shown on the case, in the header bar, in both case lists, searchable, editable, printed in the PDF | `cases` columns, `CaseCreate` / `CaseUpdate`, `CasePeople`, `NewInvestigationPage`, `CaseDetailPage`, `report.py`; the database upgrades itself (`add_missing_columns`) |
| Version comparison: side by side, version numbers, instructions, timestamps, select for editing, download, never overwritten | `VersionCard`, `VersionCompare`; append-only table + unique constraints |
| Per-case workspace, notes, auth with hashed passwords, tokens, authorisation | scrypt, JWT, owner-or-admin checks, append-only notes |
| Dataset integration: CUFS / CUFSF / UoM-SGFS investigated (licences, access, citation), not auto-downloaded; custom dataset with CSV template, JSON Schema, validator script, small clearly labelled synthetic demo, docs, translation-review status | [DATASETS.md](DATASETS.md), `datasets/custom/`, `scripts/validate_custom_dataset.py` |
| Model adapter interface (generate, edit, validate image, errors, unavailable states); honest "setup required"; never fake output as AI | `sketch_models/` ; schematic engine labelled "not AI" in UI, DB, downloads and PDF; mocks only in tests |
| Dataset and AI Evaluation page: real counts only (zero if absent), model status, last evaluation date, parser evaluation with n, no fabricated metrics | `DatasetsPage`, `GET /api/engines`, `ModelEvaluation` rows only from real runs |
| PDF case report with metadata, witness text, attributes, selected sketch, version history, instructions, notes, timestamp, disclaimers | `services/report.py`; tested by reading the PDF back |
| DB tables: Users, Cases, WitnessDescriptions, SketchVersions, InvestigatorNotes, DatasetRecords, ModelEvaluations (+ ActivityLog, DatasetInspection) | `app/models` |
| Endpoints (register, login, cases CRUD, descriptions/parse, sketches/generate, sketches/{id}/revise, sketch-versions, notes, datasets/status, datasets/inspect, evaluations, report), all documented with OpenAPI | `docs/API.md` (generated), `/docs`, `/redoc`; a test fails if the generated docs are stale |
| Responsible-use disclaimers; no automated identification or matching | registration acknowledgement, banner on every page, Settings, PDF, API docs |
| Design: dark charcoal / navy with subtle cyan, responsive, accessible, loading / empty / error states, no fake stats, no do-nothing buttons, no unneeded animation | verified in a real browser (desktop and phone) and with axe |
| No camera or microphone permission requested | `Permissions-Policy: camera=(), microphone=(), geolocation=()` on every response (tested) |
| Tests (frontend and backend, synthetic data) | section 1 |
| README with beginner-friendly VS Code on Windows steps and exact commands | [../README.md](../README.md), [../backend/README.md](../backend/README.md) |

## 3. Limitations (please read)

**AI and models**
1. **No AI engine was run end to end.** The Hugging Face / OpenAI / diffusers adapters follow the documented APIs and are tested with stand-in
   clients only. Expect to adjust model names, provider options or error handling once you use real credentials. The local diffusers adapter is an
   untested scaffold.
2. **No quality evaluation of sketch generation exists** for any engine (no suitable benchmark). Do not infer one from the UI.
3. AI engines may **invent details** and carry biases; unspecified features are decided by the model. Free-text details only reach AI engines.
4. The **schematic engine is a generic diagram**, not a likeness. It draws the 12 attributes only: skin colour is the one colour it knows (three tones; hair, eyes and clothes stay grey; no scars, accessories,
   expression). Apparent gender and age change only proportions, lashes and lines.

**Language support**
5. The parser is **rule-based**. Hindi and Kannada word lists were written by the developer and **not reviewed by native speakers**; they are small
   next to the English list. Real witness language will be messier than the synthetic examples.
6. Comparative instructions ("thicker", "broader") work in English only; Hindi / Kannada instructions support explicit values and removals.
7. The evaluation data and the word lists share an author, so scores are optimistic; the test split is no longer a clean holdout (full history in [EVALUATION.md](EVALUATION.md)).
8. Negation is recognised within three words; conflicts only between nearby statements; ages under 18 are refused; one person per description.

**Data**
9. None of the three published datasets is installed or included; the app cannot use them until you obtain them lawfully. They are photo-sketch pairs and could not
   train text-to-sketch generation anyway. The custom dataset is 90 synthetic rows.

**Security and operations**
10. Logout is client-side: tokens are stateless and stay valid until they expire (8 h by default). There is no refresh token, password reset, e-mail verification or 2FA.
11. Login throttling and sketch rate limits are in memory (per process). Behind several workers they are per worker.
12. HTTPS is not terminated by the app; use a reverse proxy in production. CSP allows inline *styles* (React sets some); scripts are not inline.
13. No migration framework: tables are created with `create_all`, and a small start-up step (`add_missing_columns`) adds *new nullable or defaulted columns* to an existing database - that is how the two name columns reach an older database. Any other schema change (rename, drop, new required column) still needs a hand-written migration, and the app refuses to start rather than guess. SQLite allows one writer at a time.
14. The audit log is not tamper-proof; there is no export. Cases cannot be shared between investigators (owner or administrator only).
15. Saved descriptions' reviewed attributes can be corrected through the API (`PUT`), but the UI lets you correct attributes only before saving and when generating.

**Other**
16. Accessibility: automated checks pass, but no manual screen-reader testing was done. Only Chromium was exercised.
17. The PDF supports Latin, Devanagari and Kannada text (bundled fonts) and A4 paper only; times are UTC in the PDF and local time in the app.

**Skin colour and names (added later)**
18. Skin colour has **three coarse values**. "Dark" is read as black, "fair / pale / light" as white, "wheatish / dusky / medium / olive / tan" as brown; the
    labels say so ("Black / dark"), and a witness meaning dark *brown* must be corrected by the investigator. Hair, eye and clothes colour are not supported.
19. **AI engines and skin colour are untested** with a real model: the prompt asks for a colour-pencil sketch and names the colour, but whether a model follows it
    (or recolours more than the face, ears and neck) is unknown. The Hindi and Kannada skin-colour words are drafts like the rest of those lists; the 18 dataset
    rows that test them were written by the same developer, so 18/18 proves little.
20. A bare "a dark man" or "a fair man" is **not** read (it could mean hair); "a white / black / brown man" is. Colour words next to hair, clothes or a mask are
    reported as "not converted", never as a skin colour.
21. **Names are personal data and are stored in plain text** in the local SQLite file (no field encryption, retention rule or anonymisation tool). They are not
    written to the activity log, only the case owner or an administrator can find them, deleting a case deletes them, and they are printed in the PDF.
    A case has one investigator name and one witness name; another witness is recorded through the label of their description. A witness who must stay anonymous
    can be entered as a code such as W-01. Older cases show "Not recorded" until someone adds the names.

## 4. Remaining work / suggested next steps

1. Have native Hindi and Kannada speakers review the word lists and the translations; then mark rows `reviewed` through the documented workflow.
2. Write an **independent** test set (different authors, real-style wording) and re-evaluate; extend the vocabulary (hair / eye colour, finer skin tones, marks) with the schematic renderer.
3. Try a real AI engine with your credentials, record its behaviour, add a human evaluation protocol for the sketches it produces, and test Hindi / Kannada instructions.
4. Obtain CUFS / CUFSF / UoM-SGFS under their terms if photo-sketch research is in scope; add pairing logic to the inspector.
5. Production hardening: server-side token revocation or short-lived tokens with refresh, shared rate-limit store, HTTPS deployment guide, Alembic migrations, PostgreSQL.
6. UI: edit reviewed attributes of a saved description; case sharing; audit-log export; manual accessibility review; test in Firefox and Safari.

## 5. Where things are (files created)

* Frontend: `package.json`, `vite.config.ts`, `tsconfig*.json`, `.oxlintrc.json`, `.npmrc`, `index.html`, `src/**` (pages, components, hooks, services, types, utils, tests), `e2e/*.spec.ts`, `playwright.config.ts`.
* Backend: `backend/app/**` (api, core, models, schemas, services), `backend/scripts/*.py`, `backend/tests/*.py`, `backend/requirements*.txt`, `backend/.env.example`.
* Data: `backend/datasets/custom/*` (CSV with 90 rows, template, JSON Schema, README, 6 schematic images), `backend/datasets/metadata/external_datasets.json`, READMEs for `external/` and `processed/`.
* Documentation: `README.md`, `backend/README.md`, `docs/*.md`, generated `docs/API.md` and `docs/openapi.json`, `docs/screenshots/*.png` (captured from a run with synthetic data).
* Fonts: `backend/app/assets/fonts/` - Noto Sans, Noto Sans Devanagari, Noto Sans Kannada with their SIL OFL licence texts.
