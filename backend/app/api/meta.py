from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import APP_NAME, APP_VERSION, get_settings
from app.core.database import get_db
from app.models import CASE_STATUSES
from app.services import disclaimers
from app.services.attributes import LANGUAGES, MAX_ADDITIONAL_DETAILS, VOCABULARY_VERSION, meta_payload
from app.services.description_parser import PARSER_NAME, PARSER_VERSION, get_parser

router = APIRouter(tags=["Meta"])


@router.get("/health", summary="Is the server (and its database) up?")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


@router.get(
    "/meta/attributes", summary="Controlled vocabulary and shared texts",
    description="The single source of truth for attribute names, allowed values and labels. The web UI builds its "
    "forms from this, so it can never offer a value the backend would reject. No sign-in needed.",
)
def vocabulary() -> dict:
    settings = get_settings()
    return {
        "app": {"name": APP_NAME, "version": APP_VERSION},
        "vocabulary_version": VOCABULARY_VERSION,
        "attributes": meta_payload(),
        "languages": list(LANGUAGES),
        "case_statuses": list(CASE_STATUSES),
        "max_additional_details": MAX_ADDITIONAL_DETAILS,
        "parser": {"name": PARSER_NAME, "version": PARSER_VERSION, "lexicon_status": get_parser().lexicon_status()},
        "disclaimers": {
            "preliminary": disclaimers.PRELIMINARY,
            "no_identification": disclaimers.NO_IDENTIFICATION,
            "responsible_use": disclaimers.RESPONSIBLE_USE,
        },
        "registration_open": settings.allow_registration,
    }
