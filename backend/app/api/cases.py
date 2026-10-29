from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Case, InvestigatorNote, User
from app.schemas.cases import CaseCreate, CaseDetail, CaseList, CaseUpdate, NoteCreate, NoteOut
from app.schemas.common import ErrorBody
from app.services import cases as case_service
from app.services import storage
from app.services.activity import log_activity

router = APIRouter(prefix="/cases", tags=["Cases"])
NOT_FOUND = {404: {"model": ErrorBody, "description": "Case not found (or not yours)"}}

SORTS = {
    "updated_desc": Case.updated_at.desc(),
    "created_desc": Case.created_at.desc(),
    "title_asc": func.lower(Case.title).asc(),
    "incident_desc": Case.incident_date.desc(),
}


@router.post("", response_model=CaseDetail, status_code=201, summary="Open a new case",
             description="Creates a case and generates its unique ID (`SA-<year>-<6 characters>`).")
def create_case(body: CaseCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CaseDetail:
    for _ in range(3):  # the unique constraint is the final guard against an ID clash
        case = Case(
            case_id=case_service.new_case_id(db), title=body.title, incident_date=body.incident_date,
            incident_description=body.incident_description, investigator_ref=body.investigator_ref, owner_id=user.id,
            investigator_name=body.investigator_name, witness_name=body.witness_name,
        )  # fmt: skip
        db.add(case)
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
    else:
        raise AppError(500, "Could not create a unique case ID. Please try again.", "case_id_unavailable")
    log_activity(db, user=user, case=case, action="case_created", summary=f"Opened case {case.case_id}")
    db.commit()
    return case_service.detail(db, case)


@router.get("", response_model=CaseList, summary="List and search cases")
def list_cases(
    q: str | None = Query(default=None, max_length=100, description="Matches case ID, title, investigator reference, investigator name or witness name."),
    status: Literal["in_progress", "under_review", "closed"] | None = None,
    sort: Literal["updated_desc", "created_desc", "title_asc", "incident_desc"] = "updated_desc",
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseList:
    stmt = select(Case)
    if user.role != "admin":
        stmt = stmt.where(Case.owner_id == user.id)
    if status:
        stmt = stmt.where(Case.status == status)
    if q and q.strip():
        like = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        stmt = stmt.where(or_(Case.case_id.ilike(like, escape="\\"), Case.title.ilike(like, escape="\\"),
                              Case.investigator_ref.ilike(like, escape="\\"), Case.investigator_name.ilike(like, escape="\\"),
                              Case.witness_name.ilike(like, escape="\\")))  # fmt: skip
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(SORTS[sort], Case.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return CaseList(items=case_service.summaries_for(db, list(rows)), total=total, page=page, page_size=page_size)


@router.get("/{case_id}", response_model=CaseDetail, responses=NOT_FOUND, summary="One case")
def get_case(case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CaseDetail:
    return case_service.detail(db, case_service.get_case_or_404(db, case_id, user))


@router.patch("/{case_id}", response_model=CaseDetail, responses={**NOT_FOUND, 409: {"model": ErrorBody}},
              summary="Edit a case, change its status or reopen it",
              description="Set `status` to `in_progress` to reopen a closed case. A closed case can only have its status changed.")
def update_case(case_id: str, body: CaseUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CaseDetail:
    case = case_service.get_case_or_404(db, case_id, user)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise AppError(422, "Nothing to change.", "empty_update")
    if case.status == "closed" and set(changes) - {"status"} and changes.get("status", "closed") == "closed":
        raise AppError(409, "This case is closed. Reopen it before editing its details.", "case_closed")
    previous = case.status
    for field, value in changes.items():
        if field in ("title", "incident_date", "investigator_ref", "investigator_name", "witness_name", "status") and value is None:
            raise AppError(422, f"{field} cannot be empty.", "validation_error")
        setattr(case, field, value)
    if "status" in changes and changes["status"] != previous:
        verb = "Reopened" if previous == "closed" else "Changed status of"
        log_activity(db, user=user, case=case, action="case_status",
                     summary=f"{verb} case {case.case_id}: {previous} -> {case.status}")  # fmt: skip
    else:
        log_activity(db, user=user, case=case, action="case_updated", summary=f"Edited details of case {case.case_id}")
    db.commit()
    return case_service.detail(db, case)


@router.delete("/{case_id}", status_code=204, responses=NOT_FOUND, summary="Delete a case and all its data",
               description="Removes the case, its descriptions, notes, sketch versions and stored image files. This cannot be undone.")
def delete_case(case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    case = case_service.get_case_or_404(db, case_id, user)
    ref, pk = case.case_id, case.id
    log_activity(db, user=user, case=None, case_ref=ref, action="case_deleted", summary=f"Deleted case {ref}")
    db.delete(case)
    db.commit()
    storage.delete_case_files(pk)
    return Response(status_code=204)


@router.get("/{case_id}/notes", response_model=list[NoteOut], responses=NOT_FOUND, summary="Investigator notes of a case")
def list_notes(case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[NoteOut]:
    case = case_service.get_case_or_404(db, case_id, user)
    return [_note_out(n) for n in case.notes]


@router.post("/{case_id}/notes", response_model=NoteOut, status_code=201, responses={**NOT_FOUND, 409: {"model": ErrorBody}},
             summary="Add a note", description="Notes are append-only: they cannot be edited or deleted, to keep an audit trail.")
def add_note(case_id: str, body: NoteCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> NoteOut:
    from app.models import SketchVersion

    case = case_service.get_case_or_404(db, case_id, user)
    case_service.require_open(case)
    if body.sketch_version_id is not None:
        version = db.get(SketchVersion, body.sketch_version_id)
        if version is None or version.case_pk != case.id:
            raise AppError(422, "That sketch version does not belong to this case.", "validation_error", fields={"sketch_version_id": "Unknown version"})
    note = InvestigatorNote(case_pk=case.id, author_id=user.id, body=body.body, sketch_version_id=body.sketch_version_id)
    db.add(note)
    case.updated_at = note.created_at or case.updated_at
    db.flush()
    log_activity(db, user=user, case=case, action="note_added", summary=f"Added a note to case {case.case_id}")
    db.commit()
    return _note_out(note)


def _note_out(note: InvestigatorNote) -> NoteOut:
    return NoteOut(id=note.id, body=note.body, sketch_version_id=note.sketch_version_id,
                   author_username=note.author.username if note.author else None, created_at=note.created_at)  # fmt: skip
