from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import AppError
from app.models import User, WitnessDescription
from app.schemas.common import ErrorBody
from app.schemas.descriptions import (
    DescriptionCreate,
    DescriptionOut,
    DescriptionUpdate,
    ParseRequest,
    ParseResponse,
)
from app.services import cases as case_service
from app.services.activity import log_activity
from app.services.attributes import ATTRIBUTE_KEYS
from app.services.description_parser import get_parser
from app.services.description_parser.base import ParseResult

router = APIRouter(tags=["Witness descriptions"])
NOT_FOUND = {404: {"model": ErrorBody}}
NOTICE = "These values are editable estimates read from the witness's wording. Check every one against the original text."


def _to_dict_list(result: ParseResult) -> tuple[list[dict], list[dict]]:
    details = [d.__dict__ for d in result.details]
    unrecognized = [{"text": u.text, "reason": u.reason} for u in result.unrecognized]
    return details, unrecognized


def _full(attrs: dict) -> dict[str, str | None]:
    return {k: attrs.get(k) or None for k in ATTRIBUTE_KEYS}


def _out(d: WitnessDescription) -> DescriptionOut:
    extracted, confirmed = _full(d.extracted_attributes), _full(d.confirmed_attributes)
    return DescriptionOut(
        id=d.id, label=d.label, language=d.language, original_text=d.original_text, extracted_attributes=extracted,
        confirmed_attributes=confirmed, additional_details=d.additional_details, parse_details=d.parse_details,
        unrecognized=d.unrecognized, warnings=d.warnings, parser_version=d.parser_version, created_at=d.created_at,
        updated_at=d.updated_at, review_status="edited_by_investigator" if extracted != confirmed else "parser_output",
    )  # fmt: skip


@router.post(
    "/descriptions/parse", response_model=ParseResponse, summary="Read a witness description (nothing is saved)",
    description="Extracts candidate attributes from English, Kannada or Hindi text with a rule-based parser. "
    "Every value comes with the words that caused it. Phrases that were not understood are returned in "
    "`unrecognized`, never guessed. This is NOT a trained AI model and gives no confidence score.",
)
def parse_description(body: ParseRequest, _: User = Depends(get_current_user)) -> ParseResponse:
    result = get_parser().parse(body.text, body.language)
    details, unrecognized = _to_dict_list(result)
    return ParseResponse(
        attributes=_full(result.attributes), details=details, unrecognized=unrecognized,  # type: ignore[arg-type]
        conflicts=[c.__dict__ for c in result.conflicts], warnings=result.warnings,  # type: ignore[arg-type]
        declared_language=result.declared_language, detected_scripts=result.detected_scripts,
        parser_name=result.parser_name, parser_version=result.parser_version, lexicon_status=result.lexicon_status, notice=NOTICE,
    )  # fmt: skip


@router.get("/cases/{case_id}/descriptions", response_model=list[DescriptionOut], responses=NOT_FOUND, summary="Saved descriptions of a case")
def list_descriptions(case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[DescriptionOut]:
    case = case_service.get_case_or_404(db, case_id, user)
    return [_out(d) for d in case.descriptions]


@router.post(
    "/cases/{case_id}/descriptions", response_model=DescriptionOut, status_code=201, responses={**NOT_FOUND, 409: {"model": ErrorBody}},
    summary="Save a witness description with its reviewed attributes",
    description="The server parses the text itself (it never trusts client-supplied extraction) and stores the original text "
    "unchanged. `confirmed_attributes` are the values after the investigator's review; if omitted, the parser's output is used.",
)
def save_description(case_id: str, body: DescriptionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DescriptionOut:
    case = case_service.get_case_or_404(db, case_id, user)
    case_service.require_open(case)
    result = get_parser().parse(body.original_text, body.language)
    details, unrecognized = _to_dict_list(result)
    extracted = _full(result.attributes)
    confirmed = _full(body.confirmed_attributes) if body.confirmed_attributes is not None else extracted
    d = WitnessDescription(
        case_pk=case.id, label=body.label, language=body.language, original_text=body.original_text,
        extracted_attributes=extracted, confirmed_attributes=confirmed, additional_details=body.additional_details,
        parse_details=details, unrecognized=unrecognized, warnings=result.warnings, parser_version=result.parser_version,
        created_by=user.id,
    )  # fmt: skip
    db.add(d)
    case.updated_at = d.created_at or case.updated_at
    db.flush()
    log_activity(db, user=user, case=case, action="description_saved", summary=f"Saved a {body.language} witness description for {case.case_id}")
    db.commit()
    return _out(d)


@router.put(
    "/cases/{case_id}/descriptions/{description_id}", response_model=DescriptionOut, responses={**NOT_FOUND, 409: {"model": ErrorBody}},
    summary="Update the reviewed attributes of a saved description",
    description="Only the reviewed attributes and the free-text details can change. The original witness text is never edited.",
)
def update_description(case_id: str, description_id: int, body: DescriptionUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DescriptionOut:
    case = case_service.get_case_or_404(db, case_id, user)
    case_service.require_open(case)
    d = db.scalar(select(WitnessDescription).where(WitnessDescription.id == description_id, WitnessDescription.case_pk == case.id))
    if d is None:
        raise AppError(404, "Description not found.", "description_not_found")
    d.confirmed_attributes = _full(body.confirmed_attributes)
    d.additional_details = body.additional_details
    log_activity(db, user=user, case=case, action="description_updated", summary=f"Updated reviewed attributes for {case.case_id}")
    db.commit()
    return _out(d)
