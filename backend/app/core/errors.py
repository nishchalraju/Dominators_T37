"""Consistent error responses.

Every error body has the same shape so the frontend can show useful messages:

    {"detail": "human readable message", "code": "machine_code", ...extra fields}
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("sketchassist.errors")


class AppError(HTTPException):
    """An expected error with a stable machine-readable code."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str,
        *,
        headers: dict[str, str] | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code
        self.extra = extra


def _field_name(loc: tuple) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path")]
    return ".".join(parts) or "body"


def _clean_message(msg: str) -> str:
    # pydantic prefixes custom validator errors with "Value error, "
    return msg.removeprefix("Value error, ")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        body = {"detail": exc.detail, "code": exc.code, **exc.extra}
        return JSONResponse(body, status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            401: "not_authenticated",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
        }.get(exc.status_code, "http_error")
        return JSONResponse(
            {"detail": exc.detail if isinstance(exc.detail, str) else "Request failed", "code": code},
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, str] = {}
        for err in exc.errors():
            fields.setdefault(_field_name(tuple(err.get("loc", ()))), _clean_message(err.get("msg", "Invalid value")))
        return JSONResponse(
            {"detail": "Some fields are missing or invalid.", "code": "validation_error", "fields": fields},
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        request_id = uuid.uuid4().hex[:12]
        log.exception("Unhandled error (request_id=%s) on %s %s", request_id, request.method, request.url.path)
        return JSONResponse(
            {
                "detail": "Something went wrong on the server. Please try again.",
                "code": "internal_error",
                "request_id": request_id,
            },
            status_code=500,
        )
