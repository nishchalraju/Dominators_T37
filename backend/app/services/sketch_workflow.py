"""Creating sketch versions: the rules that keep the evidence trail trustworthy.

* Versions are append-only. A revision is a NEW row and a NEW file; nothing is overwritten.
* The engine that really produced an image is stored with it (and whether it is AI).
* There is no fallback: if the requested engine is unavailable the request fails with a clear
  error. A rule-based drawing is never passed off as AI output.
"""

from __future__ import annotations

import io
import logging

from PIL import Image
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Case, SketchVersion, User, WitnessDescription
from app.services import storage
from app.services.activity import log_activity
from app.services.attributes import Attributes, clean_attributes
from app.services.description_parser import get_parser
from app.services.description_parser.revision import interpret_revision
from app.services.image_tools import sha256_hex
from app.services.sketch_models import (
    EditRequest,
    GenerationRequest,
    ModelError,
    ModelOutput,
    ModelUnavailableError,
    get_model,
    resolve_ai_engine,
)
from app.services.sketch_models.prompts import english_change_summary

log = logging.getLogger("sketchassist.sketches")


def _choose_engine(choice: str):
    try:
        return get_model("schematic") if choice == "schematic" else resolve_ai_engine()
    except ModelUnavailableError as exc:
        raise _unavailable(exc) from exc


def _unavailable(exc: ModelUnavailableError) -> AppError:
    return AppError(503, exc.user_message, "model_unavailable", engine=exc.engine, setup_steps=exc.setup_steps)


def _model_error(exc: ModelError) -> AppError:
    if isinstance(exc, ModelUnavailableError):
        return _unavailable(exc)
    status = 504 if exc.retryable and exc.status is None else 502
    return AppError(status, exc.user_message, exc.code, engine=exc.engine, retryable=exc.retryable)


def _next_version_number(db: Session, case_pk: int) -> int:
    return (db.scalar(select(func.max(SketchVersion.version_number)).where(SketchVersion.case_pk == case_pk)) or 0) + 1


def _store(db: Session, *, case: Case, user: User, output: ModelOutput, attributes: Attributes, kind: str, parent: SketchVersion | None,
           description_id: int | None, instruction: str, language: str | None, target_attribute: str | None,
           revision_details: dict, additional_details: str, extra_notes: list[str]) -> SketchVersion:  # fmt: skip
    """Write the image file and the database row. Retries once if two requests race for a version number."""
    with Image.open(io.BytesIO(output.png)) as img:
        width, height = img.size
    relative = storage.save_sketch_png(case.id, output.png)
    try:
        version: SketchVersion | None = None
        for attempt in (1, 2):  # a second try covers two requests racing for the same version number
            candidate = SketchVersion(
                case_pk=case.id, description_id=description_id, version_number=_next_version_number(db, case.id),
                parent_id=parent.id if parent else None, kind=kind, instruction=instruction, instruction_language=language,
                target_attribute=target_attribute, revision_details=revision_details, attributes=attributes,
                engine=output.engine, is_ai_generated=output.is_ai_generated, model_name=output.model_name,
                model_params=output.params, prompt_used=output.prompt_used, notes=[*output.notes, *extra_notes],
                additional_details=additional_details, image_path=relative, image_sha256=sha256_hex(output.png),
                width=width, height=height, file_size=len(output.png), is_selected=False, created_by=user.id,
            )  # fmt: skip
            try:
                with db.begin_nested():  # SAVEPOINT: a clash undoes only this insert
                    db.add(candidate)
                version = candidate
                break
            except IntegrityError:
                if attempt == 2:
                    raise
        assert version is not None
        # the newest version becomes the working copy; any version can be selected again later
        db.execute(update(SketchVersion).where(SketchVersion.case_pk == case.id).values(is_selected=False))
        version.is_selected = True
        return version
    except Exception:
        storage.resolve(relative).unlink(missing_ok=True)  # do not leave an orphan file behind
        raise


def create_initial_sketch(db: Session, *, case: Case, user: User, attributes: Attributes | None, additional_details: str | None,
                          engine_choice: str, description: WitnessDescription | None) -> SketchVersion:  # fmt: skip
    attrs = clean_attributes(attributes if attributes is not None else (description.confirmed_attributes if description else {}))
    details = additional_details if additional_details is not None else (description.additional_details if description else "")
    if not attrs and not (engine_choice == "ai" and details.strip()):
        raise AppError(422, "Choose at least one attribute before generating a sketch.", "no_attributes")
    model = _choose_engine(engine_choice)
    try:
        output = model.generate(GenerationRequest(attributes=attrs, additional_details=details if model.is_ai else ""))
    except ModelError as exc:
        log.info("Generation failed on engine %s: %s", exc.engine, exc.code)
        raise _model_error(exc) from exc
    notes: list[str] = []
    if details.strip() and not model.is_ai:
        notes.append("Free-text details were not used: only AI engines can use them.")
    version = _store(
        db, case=case, user=user, output=output, attributes=attrs, kind="initial", parent=None,
        description_id=description.id if description else None, instruction="", language=None, target_attribute=None,
        revision_details={}, additional_details=details if model.is_ai else "", extra_notes=notes,
    )  # fmt: skip
    case.updated_at = version.created_at
    log_activity(db, user=user, case=case, action="sketch_generated",
                 summary=f"Generated sketch version {version.version_number} ({output.engine}{', AI' if output.is_ai_generated else ', not AI'})")  # fmt: skip
    return version


def create_revision(db: Session, *, parent: SketchVersion, case: Case, user: User, instruction: str, language: str,
                    engine_choice: str | None) -> SketchVersion:  # fmt: skip
    choice = engine_choice or ("ai" if parent.is_ai_generated else "schematic")
    plan = interpret_revision(get_parser(), instruction, parent.attributes, language)

    if choice == "schematic":
        if parent.is_ai_generated:
            raise AppError(
                422,
                "This sketch was made by an AI engine. The schematic engine cannot edit it - it would redraw a different "
                "picture from the attributes. Choose the AI engine, or generate a new schematic sketch.",
                "engine_mismatch",
            )
        if not plan.changes:
            raise AppError(
                422,
                "No supported change was found in the instruction, so nothing was changed.",
                "no_supported_change",
                ignored=[{"text": u.text, "reason": u.reason} for u in plan.ignored],
                notes=plan.notes,
            )
    model = _choose_engine(choice)
    try:
        base_png = storage.read_bytes(parent.image_path)
    except storage.StorageError as exc:
        raise AppError(410, "The image file of this version is missing from storage.", "image_missing") from exc

    request = EditRequest(
        base_png=base_png, base_attributes=dict(parent.attributes), new_attributes=plan.new_attributes,
        instruction=instruction, instruction_language=language,
        change_summary_en=english_change_summary([(c.attribute, c.before, c.after) for c in plan.changes]),
        additional_details=parent.additional_details if model.is_ai else "",
    )  # fmt: skip
    try:
        output = model.edit(request)
    except ModelError as exc:
        log.info("Revision failed on engine %s: %s", exc.engine, exc.code)
        raise _model_error(exc) from exc

    extra: list[str] = list(plan.warnings)
    if model.is_ai and not plan.changes:
        extra.append("No structured attribute changed. The instruction was sent to the AI model as free text.")
    if parent.engine != output.engine:
        extra.append(f"Previous version {parent.version_number} was made by '{parent.engine}'; this version by '{output.engine}'.")
    details = {
        "changes": [c.__dict__ for c in plan.changes],
        "ignored": [{"text": u.text, "reason": u.reason} for u in plan.ignored],
        "notes": plan.notes,
    }
    version = _store(
        db, case=case, user=user, output=output, attributes=plan.new_attributes, kind="revision", parent=parent,
        description_id=parent.description_id, instruction=instruction, language=language,
        target_attribute=plan.target_attribute, revision_details=details,
        additional_details=parent.additional_details if model.is_ai else "", extra_notes=extra,
    )  # fmt: skip
    case.updated_at = version.created_at
    log_activity(db, user=user, case=case, action="sketch_revised",
                 summary=f"Created version {version.version_number} from version {parent.version_number} ({output.engine})")  # fmt: skip
    return version


def select_version(db: Session, version: SketchVersion) -> SketchVersion:
    db.execute(update(SketchVersion).where(SketchVersion.case_pk == version.case_pk).values(is_selected=False))
    version.is_selected = True
    return version
