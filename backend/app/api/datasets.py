from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models import ModelEvaluation, User
from app.schemas.common import ErrorBody
from app.schemas.datasets import (
    DatasetStatus,
    DatasetStatusResponse,
    EvaluationOut,
    EvaluationRequest,
    InspectRequest,
    InspectResponse,
    InspectResult,
)
from app.services import custom_dataset, datasets as dataset_service, evaluation
from app.services.activity import log_activity
from app.services.description_parser import PARSER_NAME, PARSER_VERSION, get_parser
from app.services.description_parser.rules import LEXICON_MODULES

router = APIRouter(tags=["Datasets and evaluation"])


@router.get(
    "/datasets/status", response_model=DatasetStatusResponse, summary="Which datasets are installed, and what is in them",
    description="Counts come only from real inspections stored in the database. A dataset that is not installed shows zero "
    "records. Nothing is downloaded automatically: the three published face-sketch collections have access restrictions and "
    "must be obtained by you under their own terms.",
)
def datasets_status(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DatasetStatusResponse:
    items = [DatasetStatus(**dataset_service.status_for(db, spec)) for spec in dataset_service.SPECS.values()]
    return DatasetStatusResponse(
        datasets=items,
        totals={"records": sum(i.records for i in items), "installed_datasets": sum(1 for i in items if i.installed)},
    )


@router.post(
    "/datasets/inspect", response_model=InspectResponse, responses={403: {"model": ErrorBody}}, summary="Inspect dataset folders (admin)",
    description="Walks the dataset folder, checks that images can be opened and (for the custom dataset) validates every CSV row. "
    "Replaces the stored inventory of the inspected dataset with the fresh result.",
)
def inspect(body: InspectRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> InspectResponse:
    keys = [body.dataset_key] if body.dataset_key else list(dataset_service.SPECS)
    results = []
    for key in keys:
        outcome = dataset_service.inspect_dataset(db, key, admin)
        log_activity(db, user=admin, action="dataset_inspected", summary=f"Inspected dataset '{key}': {outcome.files_found} files/rows, {outcome.valid} valid")
        results.append(
            InspectResult(
                dataset_key=outcome.dataset_key, installed=outcome.installed, files_found=outcome.files_found, valid=outcome.valid,
                invalid=outcome.invalid, truncated=outcome.truncated, summary=outcome.summary, problems=outcome.problems,  # type: ignore[arg-type]
                notes=outcome.notes, inspected_at=outcome.inspected_at,
            )
        )
    db.commit()
    return InspectResponse(results=results)


@router.get("/evaluations", response_model=list[EvaluationOut], summary="Stored evaluation runs, newest first",
            description="Only real runs are stored. The list is empty until an administrator runs an evaluation.")
def list_evaluations(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ModelEvaluation]:
    return list(db.scalars(select(ModelEvaluation).order_by(ModelEvaluation.created_at.desc(), ModelEvaluation.id.desc()).limit(50)))


@router.post(
    "/evaluations", response_model=EvaluationOut, status_code=201, responses={403: {"model": ErrorBody}, 422: {"model": ErrorBody}},
    summary="Run the description-parser evaluation (admin)",
    description="Parses every valid example of the custom dataset in the chosen split and compares the result with its labels. "
    "The number of examples (n) is stored with the metrics. The result carries the limitations of this particular test set.",
)
def run_evaluation(body: EvaluationRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> ModelEvaluation:
    path = get_settings().datasets_dir / "custom" / custom_dataset.CSV_NAME
    report = custom_dataset.validate_file(path)
    if not report.exists or report.file_errors:
        raise AppError(422, "The custom dataset file is missing or invalid. Run the dataset inspection to see why.", "dataset_invalid")
    rows = [r.row for r in report.valid_rows if body.split == "all" or r.row["split"] == body.split]
    if body.only_reviewed_translations:
        rows = [r for r in rows if r["translation_review_status"] in ("original", "reviewed")]
    if not rows:
        raise AppError(422, "There are no valid examples for this selection, so nothing was evaluated.", "no_examples")

    metrics = evaluation.evaluate_parser(rows, get_parser())
    metrics["caveats"] = evaluation.CAVEATS
    metrics["selection"] = {"split": body.split, "only_reviewed_translations": body.only_reviewed_translations,
                            "invalid_rows_excluded": len(report.rows) - len(report.valid_rows)}  # fmt: skip
    review = ", ".join(f"{m.LANGUAGE}={m.REVIEW_STATUS}" for m in LEXICON_MODULES)
    run = ModelEvaluation(
        evaluation_type=body.evaluation_type, target_name=PARSER_NAME, target_version=f"{PARSER_VERSION} (word lists: {review})",
        dataset_name="custom_attributes (synthetic demo)", dataset_version=report.content_sha256[:12], split=body.split,
        n_examples=len(rows), metrics=metrics, status="completed", run_by=admin.id,
        notes="Synthetic, developer-authored examples. Not representative of real witness statements.",
    )  # fmt: skip
    db.add(run)
    db.flush()
    log_activity(db, user=admin, action="evaluation_run", summary=f"Parser evaluation on {len(rows)} examples (split: {body.split})")
    db.commit()
    return run
