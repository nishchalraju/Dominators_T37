"""Application entry point.

Run (from the ``backend`` folder)::

    uvicorn app.main:app --reload --port 8000

* ``/api/...``   the JSON API   (interactive docs: ``/docs``, ``/redoc``, schema: ``/openapi.json``)
* everything else: the built React app from ``../dist`` (after ``npm run build``). During development
  you normally run the Vite dev server instead, which proxies ``/api`` to this server.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.api.router import api_router
from app.core.config import APP_NAME, APP_VERSION, get_settings
from app.core.database import init_db
from app.core.errors import install_error_handlers
from app.core.logging import setup_logging
from app.services.disclaimers import NO_IDENTIFICATION, PRELIMINARY

log = logging.getLogger("sketchassist")

API_DESCRIPTION = f"""
**{APP_NAME}** - multilingual (English / Kannada / Hindi) forensic sketch assistance and case management.

> **{PRELIMINARY}** {NO_IDENTIFICATION}

### How to try it
1. `POST /api/auth/register` (the first account becomes the administrator), then use the returned `access_token`
   with the **Authorize** button above.
2. Open a case, parse a description, generate a sketch with `engine=schematic` (rule-based, not AI) and revise it.
3. AI engines need credentials (see `GET /api/engines`); without them they answer **503** with setup steps.

### Conventions
* Errors always look like `{{"detail": "...", "code": "machine_code"}}` (validation errors add `fields`).
* A case that is not yours looks exactly like a case that does not exist (404).
"""

TAGS = [
    {"name": "Meta", "description": "Health check and the controlled vocabulary."},
    {"name": "Authentication", "description": "Register, sign in, who am I."},
    {"name": "Dashboard", "description": "Numbers and recent activity, counted from the database."},
    {"name": "Cases", "description": "Create, search, edit, reopen and delete cases; investigator notes."},
    {"name": "Witness descriptions", "description": "Parse English / Kannada / Hindi descriptions into editable attributes."},
    {"name": "Sketches", "description": "Generate and revise sketches; compare, select and download versions; engine status."},
    {"name": "Datasets and evaluation", "description": "Dataset inventory and parser evaluation (real runs only)."},
    {"name": "Reports", "description": "PDF case report."},
]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds protective headers. The CSP is attached only to the app's own HTML page (not to /docs)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("Referrer-Policy", "no-referrer")
        # The app never needs the camera, microphone or location - deny them outright.
        headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        if request.url.path.startswith("/api/") and "Cache-Control" not in headers:
            headers["Cache-Control"] = "no-store"
        return response


def _csp() -> str:
    frame = get_settings().frame_ancestors.strip()
    parts = [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]
    if frame:
        parts.append(f"frame-ancestors {frame}")
    return "; ".join(parts)


def _mount_frontend(app: FastAPI, dist: Path) -> None:
    index = dist / "index.html"
    if not index.is_file():
        log.warning("Frontend build not found at %s. Run 'npm run build' (or use the Vite dev server).", dist)

        @app.get("/", include_in_schema=False)
        def no_frontend() -> JSONResponse:
            return JSONResponse(
                {"detail": "The web app has not been built yet. Run 'npm run build' in the project folder, or start "
                           "'npm run dev'. The API is available at /api and its docs at /docs.", "code": "frontend_not_built"},
                status_code=200,
            )
        return

    root = dist.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> Response:
        if path.startswith("api/") or path in ("api", "docs", "redoc", "openapi.json"):
            return JSONResponse({"detail": "Not found.", "code": "not_found"}, status_code=404)
        candidate = (dist / path).resolve()
        if path and (root in candidate.parents) and candidate.is_file():
            headers = {"Cache-Control": "public, max-age=31536000, immutable"} if candidate.parent.name == "assets" else {"Cache-Control": "no-cache"}
            return FileResponse(candidate, headers=headers)
        # any other URL is a client-side route: serve the app shell
        return FileResponse(index, headers={"Content-Security-Policy": _csp(), "Cache-Control": "no-cache"})


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        init_db()
        log.info("%s %s started (env=%s)", APP_NAME, APP_VERSION, settings.app_env)
        yield

    app = FastAPI(
        title=f"{APP_NAME} API", version=APP_VERSION, description=API_DESCRIPTION, openapi_tags=TAGS, lifespan=lifespan,
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
    )  # fmt: skip
    install_error_handlers(app)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Content-Disposition"],
        allow_credentials=False,  # tokens travel in the Authorization header, not cookies
    )
    app.include_router(api_router)
    _mount_frontend(app, settings.frontend_dist_dir)
    return app


app = create_app()
