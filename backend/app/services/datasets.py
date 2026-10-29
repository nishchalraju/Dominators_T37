"""Dataset registry and inspection.

Nothing is downloaded by this application. The three published face-sketch collections are
listed with how to obtain them legitimately; the inspector only looks at files a person has
placed in ``backend/datasets/external/<key>/`` and reports what is really there (zero if empty).
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import utcnow
from app.models import DatasetInspection, DatasetRecord, User
from app.services import custom_dataset

log = logging.getLogger("sketchassist.datasets")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".gif"}
IGNORED_NAMES = {".gitkeep", ".gitignore", ".ds_store", "thumbs.db", "readme.md", "readme.txt"}
MAX_FILES_PER_INSPECTION = 20_000
MAX_PROBLEMS_RETURNED = 50


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    name: str
    kind: str  # external | custom
    description: str
    licence: str
    access: str
    citation: str
    source_url: str
    subdir: str


SPECS: dict[str, DatasetSpec] = {
    "cufs": DatasetSpec(
        key="cufs",
        name="CUHK Face Sketch Database (CUFS)",
        kind="external",
        description=(
            "606 face-sketch pairs: 188 CUHK students, 123 AR and 295 XM2VTS faces. Each sketch was drawn by an artist "
            "from a frontal, neutral-expression photo. These are photo-sketch pairs, not text-sketch pairs."
        ),
        licence="Research use only, no commercial use, citation required. The AR and XM2VTS photos have separate third-party terms.",
        access=(
            "Follow the instructions on the CUHK MMLab datasets page. Photos for the AR part come from the Purdue AR "
            "database site and for the XM2VTS part from the Surrey XM2VTSDB, each under its own agreement. Verify the "
            "current terms at the source before use."
        ),
        citation="X. Wang and X. Tang, 'Face Photo-Sketch Synthesis and Recognition', IEEE TPAMI 31(11), 2009.",
        source_url="https://mmlab.ie.cuhk.edu.hk/datasets.html",
        subdir="cufs",
    ),
    "cufsf": DatasetSpec(
        key="cufsf",
        name="CUHK Face Sketch FERET Database (CUFSF)",
        kind="external",
        description=(
            "1,194 persons from the FERET database. Photos have lighting variation; sketches include shape exaggeration. "
            "Sketches are provided by CUHK; the photos must come from NIST."
        ),
        licence=(
            "Sketches: research use only, citation required. Photos: the NIST Color FERET release agreement applies "
            "(no redistribution; restrictions on publishing images)."
        ),
        access=(
            "Download the sketches from the CUHK CUFSF page. Request the FERET photos from NIST (an emailed account request "
            "and a signed release agreement are required). Verify the current terms at the source before use."
        ),
        citation="W. Zhang, X. Wang and X. Tang, 'Coupled Information-Theoretic Encoding for Face Photo-Sketch Recognition', CVPR 2011.",
        source_url="https://mmlab.ie.cuhk.edu.hk/archive/cufsf/",
        subdir="cufsf",
    ),
    "uom_sgfs": DatasetSpec(
        key="uom_sgfs",
        name="UoM-SGFS (University of Malta software-generated composite sketches)",
        kind="external",
        description=(
            "Colour composite sketches made with EFIT-V software for 300 Color-FERET subjects (Sets A and B). "
            "This is the closest published data to real composite-sketch practice. FERET photos are not included."
        ),
        licence="Access via a request form; the dataset page states it may be used as provided. Citation required. FERET photos need their own NIST agreement.",
        access="Use the request form linked from the University of Malta page. Verify the current terms at the source before use.",
        citation="C. Galea and R. A. Farrugia, BIOSIG 2016 (see the dataset page for the exact reference).",
        source_url="https://staff.um.edu.mt/reuben.farrugia/codedata/uom-sgfs",
        subdir="uom_sgfs",
    ),
    "custom_attributes": DatasetSpec(
        key="custom_attributes",
        name="Custom attribute dataset (synthetic demo)",
        kind="custom",
        description=(
            "Hand-written description / attribute pairs in English, Kannada and Hindi for testing the description parser. "
            "SYNTHETIC: no real people and no photographs. Kannada and Hindi rows are developer-written translations "
            "that have not been reviewed by native speakers."
        ),
        licence="Created for this project (synthetic data). Replace or extend it with your own consented / licensed data using the same CSV format.",
        access="Included in backend/datasets/custom/. See backend/datasets/custom/README.md for the format and the review workflow.",
        citation="Not applicable (project-authored).",
        source_url="",
        subdir="",
    ),
}


def dataset_dir(spec: DatasetSpec) -> Path:
    base = get_settings().datasets_dir
    return base / "custom" if spec.kind == "custom" else base / "external" / spec.subdir


def expected_path(spec: DatasetSpec) -> str:
    return "backend/datasets/custom/" if spec.kind == "custom" else f"backend/datasets/external/{spec.subdir}/"


def _real_files(root: Path):
    if not root.is_dir():
        return
    for path in root.rglob("*"):
        if path.is_file() and path.name.lower() not in IGNORED_NAMES and not path.name.startswith("."):
            yield path


def is_installed(spec: DatasetSpec) -> bool:
    root = dataset_dir(spec)
    if spec.kind == "custom":
        return (root / custom_dataset.CSV_NAME).is_file()
    return next(_real_files(root), None) is not None


# --------------------------------------------------------------------------- inspection
@dataclass
class InspectionOutcome:
    dataset_key: str
    installed: bool
    files_found: int
    valid: int
    invalid: int
    truncated: bool
    summary: dict
    problems: list[dict]
    notes: list[str]
    inspected_at: datetime


def _inspect_external(db: Session, spec: DatasetSpec, user: User | None) -> InspectionOutcome:
    root = dataset_dir(spec)
    records: list[DatasetRecord] = []
    by_ext: Counter[str] = Counter()
    by_role: Counter[str] = Counter()
    formats: Counter[str] = Counter()
    problems: list[dict] = []
    files, images, readable, truncated = 0, 0, 0, False
    now = utcnow()
    for path in sorted(_real_files(root) or []):
        if files >= MAX_FILES_PER_INSPECTION:
            truncated = True
            break
        files += 1
        suffix = path.suffix.lower() or "(none)"
        by_ext[suffix] += 1
        if suffix not in IMAGE_EXTENSIONS:
            continue
        images += 1
        rel = path.relative_to(root).as_posix()
        parts = {p.lower() for p in path.relative_to(root).parts}
        role = "sketch" if any("sketch" in p for p in parts) else "photo" if any("photo" in p for p in parts) else "unknown"
        by_role[role] += 1
        info: dict = {"has_image": True, "image_readable": False, "image_format": None, "width": None, "height": None, "problems": []}
        try:
            with Image.open(path) as img:
                info.update(image_format=img.format, width=img.size[0], height=img.size[1])
                img.verify()
            info["image_readable"] = True
            readable += 1
            formats[info["image_format"] or "?"] += 1
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
            info["problems"].append("The file could not be read as an image.")
            problems.append({"record": rel, "problems": info["problems"]})
        records.append(
            DatasetRecord(
                dataset_key=spec.key, record_key=rel, source_id=path.stem, kind="image", has_image=True,
                image_readable=info["image_readable"], image_format=info["image_format"], width=info["width"],
                height=info["height"], file_size=path.stat().st_size, labelled=False, valid=info["image_readable"],
                problems=info["problems"], details={"role": role}, inspected_at=now, inspected_by=user.id if user else None,
            )
        )
    db.execute(delete(DatasetRecord).where(DatasetRecord.dataset_key == spec.key))
    db.add_all(records)
    notes = [
        "Files are counted and checked only. Pairing photos with sketches is dataset-specific and is not done here.",
        "Roles (sketch / photo) are guessed from folder names and may be 'unknown'.",
    ]
    if truncated:
        notes.append(f"Stopped after {MAX_FILES_PER_INSPECTION} files; the numbers are a lower bound.")
    if files == 0:
        notes.append("The folder is empty or missing: nothing is installed. Follow the access instructions for this dataset.")
    summary = {"images": images, "readable_images": readable, "other_files": files - images,
               "by_extension": dict(by_ext), "by_role": dict(by_role), "formats": dict(formats)}  # fmt: skip
    return InspectionOutcome(spec.key, files > 0, files, readable, images - readable, truncated, summary, problems[:MAX_PROBLEMS_RETURNED], notes, now)


def _inspect_custom(db: Session, spec: DatasetSpec, user: User | None) -> InspectionOutcome:
    root = dataset_dir(spec)
    report = custom_dataset.validate_file(root / custom_dataset.CSV_NAME)
    now = utcnow()
    records: list[DatasetRecord] = []
    problems: list[dict] = [{"record": "file", "problems": report.file_errors}] if report.file_errors else []
    for r in report.rows:
        has_image = bool(r.row["image_file"])
        records.append(
            DatasetRecord(
                dataset_key=spec.key, record_key=f"row:{r.sample_id}", source_id=r.sample_id, kind="attribute_row",
                has_image=has_image, image_readable=has_image and r.valid, labelled=any(r.row[k] for k in custom_dataset.ATTRIBUTE_KEYS),
                valid=r.valid, problems=r.errors,
                details={k: r.row[k] for k in ("language", "split", "group_id", "translation_review_status", "annotation_method", "permission_status")},
                inspected_at=now, inspected_by=user.id if user else None,
            )
        )
        if not r.valid:
            problems.append({"record": f"{r.sample_id} (line {r.line})", "problems": r.errors})
    db.execute(delete(DatasetRecord).where(DatasetRecord.dataset_key == spec.key))
    db.add_all(records)
    notes = [
        "SYNTHETIC demo data: no real people, no photographs.",
        "Kannada and Hindi rows are developer-written translations that no native speaker has reviewed.",
    ]
    if not report.exists:
        notes.append("attribute_samples.csv was not found.")
    notes.extend(report.notes)
    summary = {
        "rows": report.total, "languages": report.counts("language"), "splits": report.counts("split"),
        "translation_review_status": report.counts("translation_review_status"),
        "annotation_method": report.counts("annotation_method"), "permission_status": report.counts("permission_status"),
        "content_sha256": report.content_sha256,
    }  # fmt: skip
    return InspectionOutcome(spec.key, report.exists, report.total, len(report.valid_rows), report.total - len(report.valid_rows),
                             False, summary, problems[:MAX_PROBLEMS_RETURNED], notes, now)  # fmt: skip


def inspect_dataset(db: Session, key: str, user: User | None) -> InspectionOutcome:
    spec = SPECS[key]
    outcome = _inspect_custom(db, spec, user) if spec.kind == "custom" else _inspect_external(db, spec, user)
    db.add(DatasetInspection(dataset_key=key, installed=outcome.installed, files_found=outcome.files_found,
                             summary=outcome.summary, notes="\n".join(outcome.notes), inspected_at=outcome.inspected_at, inspected_by=user.id if user else None))  # fmt: skip
    return outcome


# --------------------------------------------------------------------------- status
def status_for(db: Session, spec: DatasetSpec) -> dict:
    last = db.scalar(select(DatasetInspection).where(DatasetInspection.dataset_key == spec.key).order_by(DatasetInspection.id.desc()))
    total = db.scalar(select(func.count(DatasetRecord.id)).where(DatasetRecord.dataset_key == spec.key)) or 0
    valid = db.scalar(select(func.count(DatasetRecord.id)).where(DatasetRecord.dataset_key == spec.key, DatasetRecord.valid.is_(True))) or 0
    labelled = db.scalar(select(func.count(DatasetRecord.id)).where(DatasetRecord.dataset_key == spec.key, DatasetRecord.labelled.is_(True))) or 0
    installed = is_installed(spec)
    notes: list[str] = []
    if spec.kind == "external" and not installed:
        notes.append("Not installed: this application never downloads restricted datasets. Obtain them as described under 'access'.")
    if last and installed != last.installed:
        notes.append("The folder changed since the last inspection. Run the inspection again.")
    if installed and last is None:
        notes.append("Files are present but have not been inspected yet, so no counts are shown.")
    review = None
    if spec.kind == "custom" and last is not None:
        review = (last.summary or {}).get("translation_review_status") or None
    return {
        "key": spec.key, "name": spec.name, "kind": spec.kind, "description": spec.description, "licence": spec.licence,
        "access": spec.access, "citation": spec.citation, "source_url": spec.source_url, "expected_path": expected_path(spec),
        "installed": installed, "inspected": last is not None, "last_inspected_at": last.inspected_at if last else None,
        "files_found": last.files_found if last else None, "records": total, "valid_records": valid, "labelled_records": labelled,
        "notes": notes, "translation_review": review,
    }  # fmt: skip
