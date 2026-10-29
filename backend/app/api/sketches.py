from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, limit_sketch_requests
from app.core.database import get_db
from app.core.errors import AppError
from app.models import Case, ModelEvaluation, SketchVersion, User, WitnessDescription
from app.schemas.common import ErrorBody
from app.schemas.sketches import (
    EngineStatusOut,
    GenerateRequest,
    ReviseRequest,
    RevisionDetails,
    SketchVersionList,
    SketchVersionOut,
)
from app.services import cases as case_service
from app.services import sketch_workflow, storage
from app.services.activity import log_activity
from app.services.image_tools import add_provenance_band, sha256_hex, thumbnail_png
from app.services.provenance import caption_for
from app.services.sketch_models import all_statuses
from app.services.sketch_models.registry import ENGINE_LABELS

router = APIRouter(tags=["Sketches"])
NOT_FOUND = {404: {"model": ErrorBody}}
MODEL_ERRORS = {
    422: {"model": ErrorBody, "description": "Nothing to draw / no supported change in the instruction"},
    503: {"model": ErrorBody, "description": "The chosen engine is not set up (the body lists the setup steps)"},
    502: {"model": ErrorBody, "description": "The engine failed or returned an unusable image"},
    429: {"model": ErrorBody, "description": "Too many requests"},
}


# --------------------------------------------------------------------------- helpers
def _version_out(version: SketchVersion, case_ref: str, numbers: dict[int, int], usernames: dict[int, str]) -> SketchVersionOut:
    base = f"/api/sketch-versions/{version.id}"
    details = RevisionDetails(**version.revision_details) if version.revision_details else None
    return SketchVersionOut(
        id=version.id, case_id=case_ref, version_number=version.version_number, parent_id=version.parent_id,
        parent_version_number=numbers.get(version.parent_id) if version.parent_id else None,
        kind=version.kind, instruction=version.instruction, instruction_language=version.instruction_language,  # type: ignore[arg-type]
        target_attribute=version.target_attribute, attributes={k: v for k, v in version.attributes.items()},
        additional_details=version.additional_details, engine=version.engine,
        engine_label=ENGINE_LABELS.get(version.engine, version.engine), is_ai_generated=version.is_ai_generated,
        model_name=version.model_name, notes=version.notes, revision_details=details, is_selected=version.is_selected,
        created_by=usernames.get(version.created_by) if version.created_by else None, created_at=version.created_at,
        width=version.width, height=version.height, file_size=version.file_size, sha256=version.image_sha256,
        image_url=f"{base}/image", thumbnail_url=f"{base}/thumbnail", download_url=f"{base}/image?download=true",
    )  # fmt: skip


def _context(db: Session, case: Case) -> tuple[dict[int, int], dict[int, str]]:
    rows = db.execute(select(SketchVersion.id, SketchVersion.version_number).where(SketchVersion.case_pk == case.id)).all()
    users = {u.id: u.username for u in db.scalars(select(User).where(User.id.in_(select(SketchVersion.created_by).where(SketchVersion.case_pk == case.id))))}
    return {i: n for i, n in rows}, users


def _single_out(db: Session, version: SketchVersion, case: Case) -> SketchVersionOut:
    numbers, users = _context(db, case)
    return _version_out(version, case.case_id, numbers, users)


def _get_version(db: Session, sketch_id: int, user: User) -> tuple[SketchVersion, Case]:
    version = db.get(SketchVersion, sketch_id)
    case = db.get(Case, version.case_pk) if version else None
    if version is None or case is None or (case.owner_id != user.id and user.role != "admin"):
        raise AppError(404, "Sketch version not found.", "sketch_not_found")
    return version, case


# --------------------------------------------------------------------------- create
@router.post(
    "/sketches/generate", response_model=SketchVersionOut, status_code=201, responses={**NOT_FOUND, **MODEL_ERRORS, 409: {"model": ErrorBody}},
    summary="Generate a sketch (creates a new version)",
    description="`engine=schematic` draws a rule-based diagram (NOT AI) and always works. `engine=ai` uses the configured AI "
    "engine and returns **503 with setup steps** if none is configured - there is never a silent fallback to the schematic "
    "engine. Attributes come from `attributes`, else from the reviewed attributes of `description_id`.",
)
def generate_sketch(body: GenerateRequest, user: User = Depends(limit_sketch_requests), db: Session = Depends(get_db)) -> SketchVersionOut:
    case = case_service.get_case_or_404(db, body.case_id, user)
    case_service.require_open(case)
    description = None
    if body.description_id is not None:
        description = db.scalar(select(WitnessDescription).where(WitnessDescription.id == body.description_id, WitnessDescription.case_pk == case.id))
        if description is None:
            raise AppError(404, "Description not found in this case.", "description_not_found")
    version = sketch_workflow.create_initial_sketch(
        db, case=case, user=user, attributes=body.attributes, additional_details=body.additional_details,
        engine_choice=body.engine, description=description,
    )  # fmt: skip
    db.commit()
    return _single_out(db, version, case)


@router.post(
    "/sketches/{sketch_id}/revise", response_model=SketchVersionOut, status_code=201, responses={**NOT_FOUND, **MODEL_ERRORS, 409: {"model": ErrorBody}},
    summary="Revise a sketch with an instruction (creates a new version)",
    description="Reads the instruction (English comparatives such as 'thicker eyebrows', explicit values and removals in English, "
    "Hindi or Kannada), turns it into attribute changes and draws a **new** version. The version you revise is never modified. "
    "Parts of the instruction that could not be applied are listed in `revision_details.ignored`.",
)
def revise_sketch(sketch_id: int, body: ReviseRequest, user: User = Depends(limit_sketch_requests), db: Session = Depends(get_db)) -> SketchVersionOut:
    parent, case = _get_version(db, sketch_id, user)
    case_service.require_open(case)
    version = sketch_workflow.create_revision(
        db, parent=parent, case=case, user=user, instruction=body.instruction, language=body.language, engine_choice=body.engine,
    )  # fmt: skip
    db.commit()
    return _single_out(db, version, case)


# --------------------------------------------------------------------------- read
@router.get("/sketch-versions", response_model=SketchVersionList, responses=NOT_FOUND, summary="All versions of a case, oldest first")
def list_versions(
    case_id: str = Query(description="Public case ID."), user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> SketchVersionList:
    case = case_service.get_case_or_404(db, case_id, user)
    versions = db.scalars(select(SketchVersion).where(SketchVersion.case_pk == case.id).order_by(SketchVersion.version_number)).all()
    numbers, users = _context(db, case)
    return SketchVersionList(case_id=case.case_id, items=[_version_out(v, case.case_id, numbers, users) for v in versions])


@router.get("/sketch-versions/{sketch_id}", response_model=SketchVersionOut, responses=NOT_FOUND, summary="One sketch version")
def get_version(sketch_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SketchVersionOut:
    version, case = _get_version(db, sketch_id, user)
    return _single_out(db, version, case)


def _read_verified(version: SketchVersion) -> bytes:
    try:
        data = storage.read_bytes(version.image_path)
    except storage.StorageError as exc:
        raise AppError(410, "The image file of this version is missing from storage.", "image_missing") from exc
    if sha256_hex(data) != version.image_sha256:  # tamper / corruption check
        raise AppError(500, "The stored image failed its integrity check and was not served.", "image_integrity_failed")
    return data


def _png(data: bytes, headers: dict[str, str]) -> Response:
    return Response(content=data, media_type="image/png", headers={"X-Content-Type-Options": "nosniff", **headers})


@router.get(
    "/sketch-versions/{sketch_id}/image", responses={**NOT_FOUND, 200: {"content": {"image/png": {}}}}, summary="The sketch image (PNG)",
    description="Requires the Authorization header. With `download=true` the PNG gets a caption band stating how the image was "
    "made (AI or not), the case, version and time, and is sent as an attachment. The stored file itself is never altered.",
)
def get_image(sketch_id: int, download: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    version, case = _get_version(db, sketch_id, user)
    data = _read_verified(version)
    if not download:
        return _png(data, {"Cache-Control": "private, max-age=3600", "ETag": f'"{version.image_sha256}"'})
    headline, lines, warning = caption_for(version, case.case_id)
    captioned = add_provenance_band(data, headline, lines, warning=warning)
    log_activity(db, user=user, case=case, action="sketch_downloaded", summary=f"Downloaded version {version.version_number} of {case.case_id}")
    db.commit()
    kind = "ai" if version.is_ai_generated else "schematic"
    filename = f"{case.case_id}_v{version.version_number}_{kind}.png"
    return _png(captioned, {"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})


@router.get("/sketch-versions/{sketch_id}/thumbnail", responses={**NOT_FOUND, 200: {"content": {"image/png": {}}}}, summary="Small preview (PNG)")
def get_thumbnail(sketch_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    version, _ = _get_version(db, sketch_id, user)
    return _png(thumbnail_png(_read_verified(version)), {"Cache-Control": "private, max-age=3600"})


@router.post(
    "/sketch-versions/{sketch_id}/select", response_model=SketchVersionOut, responses={**NOT_FOUND, 409: {"model": ErrorBody}},
    summary="Select a version as the working copy and report sketch",
    description="Exactly one version per case is selected. It is the one shown in the PDF report. Selecting never changes any image.",
)
def select_version(sketch_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SketchVersionOut:
    version, case = _get_version(db, sketch_id, user)
    case_service.require_open(case)
    sketch_workflow.select_version(db, version)
    log_activity(db, user=user, case=case, action="sketch_selected", summary=f"Selected version {version.version_number} of {case.case_id}")
    db.commit()
    return _single_out(db, version, case)


# --------------------------------------------------------------------------- engines
@router.get(
    "/engines", response_model=list[EngineStatusOut], summary="Status of every sketch engine",
    description="Shows which engines can run right now and why not. `verified` is true only after a real request succeeded since "
    "the server started. `last_evaluated_at` comes from stored evaluations and is null when an engine was never evaluated.",
)
def engines(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[EngineStatusOut]:
    last: dict[str, datetime] = dict(
        db.execute(select(ModelEvaluation.target_name, func.max(ModelEvaluation.created_at)).group_by(ModelEvaluation.target_name)).all()
    )
    out = []
    for s in all_statuses():
        out.append(
            EngineStatusOut(
                engine=s.engine, label=s.label, is_ai=s.is_ai, state=s.state, available=s.available,  # type: ignore[arg-type]
                detail=s.detail, setup_steps=s.setup_steps, supports_generate=s.supports_generate, supports_edit=s.supports_edit,
                models=s.models, licence_note=s.licence_note, verified=s.verified, last_success_at=s.last_success_at,
                last_error=s.last_error, last_error_at=s.last_error_at, last_evaluated_at=last.get(s.engine),
            )
        )
    return out
