from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import SketchVersion, User
from app.schemas.common import ErrorBody
from app.services import cases as case_service
from app.services import storage
from app.services.activity import log_activity
from app.services.report import ReportData, build_case_report

router = APIRouter(tags=["Reports"])


@router.get(
    "/cases/{case_id}/report", responses={404: {"model": ErrorBody}, 200: {"content": {"application/pdf": {}}}}, summary="Download the case report (PDF)",
    description="Includes case details, the witness text exactly as entered, the reviewed attributes, the selected sketch with its "
    "provenance caption, the full version history with instructions, investigator notes, the generation time, and the disclaimers: "
    "'preliminary investigative aid requiring human review' and 'no identification'.",
)
def case_report(case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    case = case_service.get_case_or_404(db, case_id, user)
    versions = list(db.scalars(select(SketchVersion).where(SketchVersion.case_pk == case.id).order_by(SketchVersion.version_number)))
    selected = next((v for v in versions if v.is_selected), None)
    selected_png = None
    if selected is not None:
        try:
            selected_png = storage.read_bytes(selected.image_path)
        except storage.StorageError:
            selected_png = None  # the report says no picture is available instead of failing
    owner = db.get(User, case.owner_id)
    data = ReportData(
        case=case, owner_username=owner.username if owner else "unknown", generated_by=user.username,
        generated_at=datetime.now(timezone.utc), descriptions=list(case.descriptions), versions=versions, selected=selected,
        selected_png=selected_png, notes=[(n, n.author.username if n.author else "unknown") for n in case.notes],
    )  # fmt: skip
    pdf = build_case_report(data)
    log_activity(db, user=user, case=case, action="report_generated", summary=f"Generated the PDF report for {case.case_id}")
    db.commit()
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="SketchAssist_{case.case_id}_report.pdf"', "Cache-Control": "no-store"},
    )
