"""Validation of the custom attribute dataset (``datasets/custom/attribute_samples.csv``).

One validator is used by the command-line script, the API's dataset inspector and the tests, so a
file can never pass one and fail another. Every problem names the row and the reason.
"""

from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from app.services.attributes import ATTRIBUTE_BY_KEY, ATTRIBUTE_KEYS, LANGUAGE_CODES
from app.services.image_tools import ImageValidationError, inspect_image

CSV_NAME = "attribute_samples.csv"
TEMPLATE_NAME = "attribute_samples.template.csv"
SCHEMA_NAME = "attribute_sample.schema.json"

SPLITS = ("dev", "test")
TRANSLATION_STATUSES = ("original", "unreviewed", "in_review", "reviewed")
ANNOTATION_METHODS = ("developer_authored", "annotator_labelled", "derived_from_source")
PERMISSION_STATUSES = ("synthetic_no_real_person", "consent_documented", "licensed_dataset")

COLUMNS = [
    "sample_id", "group_id", "split", "language", "description_text", *ATTRIBUTE_KEYS,
    "translation_review_status", "reviewer_id", "reviewed_on", "annotation_method", "permission_status",
    "image_file", "notes",
]  # fmt: skip
# Attribute columns added after vocabulary 1.0. A CSV written for 1.0 does not have them and stays valid;
# the validator says so (``ValidationReport.notes``) and treats those attributes as "not labelled".
LATER_ATTRIBUTE_COLUMNS = ("skin_colour",)
OPTIONAL_COLUMNS = {"reviewer_id", "reviewed_on", "image_file", "notes", *LATER_ATTRIBUTE_COLUMNS}
REQUIRED_COLUMNS = [c for c in COLUMNS if c not in OPTIONAL_COLUMNS]

MAX_ROWS = 50_000
MAX_TEXT = 4000
_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_SCRIPT_RANGES = {"hi": (0x0900, 0x097F), "kn": (0x0C80, 0x0CFF)}


@dataclass
class RowResult:
    line: int  # line number in the file (header = 1)
    sample_id: str
    row: dict[str, str]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


@dataclass
class ValidationReport:
    path: str
    exists: bool = False
    file_errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # things worth knowing that are not errors
    rows: list[RowResult] = field(default_factory=list)
    content_sha256: str = ""

    @property
    def total(self) -> int:
        return len(self.rows)

    @property
    def valid_rows(self) -> list[RowResult]:
        return [r for r in self.rows if r.valid]

    @property
    def ok(self) -> bool:
        return self.exists and not self.file_errors and all(r.valid for r in self.rows)

    def counts(self, column: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.rows:
            key = r.row.get(column, "") or "(empty)"
            out[key] = out.get(key, 0) + 1
        return dict(sorted(out.items()))


def _has_script(text: str, language: str) -> bool:
    if language == "en":
        return any(("a" <= ch.lower() <= "z") for ch in text)
    lo, hi = _SCRIPT_RANGES[language]
    return any(lo <= ord(ch) <= hi for ch in text)


def _check_row(result: RowResult, base_dir: Path) -> None:
    row, err, warn = result.row, result.errors, result.warnings
    if not _ID_RE.match(row["sample_id"]):
        err.append("sample_id must be 1-64 characters: letters, digits, _ . -")
    if row["group_id"] and not _ID_RE.match(row["group_id"]):
        err.append("group_id must be 1-64 characters: letters, digits, _ . -")
    if row["split"] not in SPLITS:
        err.append(f"split must be one of: {', '.join(SPLITS)}")
    language = row["language"]
    if language not in LANGUAGE_CODES:
        err.append(f"language must be one of: {', '.join(LANGUAGE_CODES)}")
    text = row["description_text"]
    if not text.strip():
        err.append("description_text is empty")
    elif len(text) > MAX_TEXT:
        err.append(f"description_text is longer than {MAX_TEXT} characters")
    elif language in LANGUAGE_CODES and not _has_script(text, language):
        err.append(f"description_text does not look like '{language}' (expected script not found)")

    labelled = 0
    for key in ATTRIBUTE_KEYS:
        value = row[key]
        if not value:
            continue
        labelled += 1
        if value not in ATTRIBUTE_BY_KEY[key].value_keys:
            err.append(f"{key}='{value}' is not in the vocabulary ({', '.join(ATTRIBUTE_BY_KEY[key].value_keys)})")
    if labelled == 0:
        warn.append("no attributes are labelled")

    status = row["translation_review_status"]
    if status not in TRANSLATION_STATUSES:
        err.append(f"translation_review_status must be one of: {', '.join(TRANSLATION_STATUSES)}")
    elif status == "original" and language != "en":
        err.append("'original' is only valid for English rows (Kannada / Hindi rows are translations)")
    elif status == "reviewed":
        if not row["reviewer_id"]:
            err.append("a 'reviewed' row needs reviewer_id")
        try:
            date.fromisoformat(row["reviewed_on"])
        except ValueError:
            err.append("a 'reviewed' row needs reviewed_on as YYYY-MM-DD")
    elif language != "en" and status == "original":
        err.append("'original' is only valid for English rows")
    if row["annotation_method"] not in ANNOTATION_METHODS:
        err.append(f"annotation_method must be one of: {', '.join(ANNOTATION_METHODS)}")
    if row["permission_status"] not in PERMISSION_STATUSES:
        err.append(f"permission_status must be one of: {', '.join(PERMISSION_STATUSES)}")

    image = row["image_file"]
    if image:
        target = (base_dir / image).resolve()
        if Path(image).is_absolute() or base_dir.resolve() not in target.parents:
            err.append("image_file must be a relative path inside the dataset folder")
        elif not target.is_file():
            err.append(f"image_file '{image}' does not exist")
        else:
            try:
                inspect_image(target.read_bytes())
            except ImageValidationError as exc:
                err.append(f"image_file '{image}' is not a usable image: {exc}")


def validate_file(path: Path) -> ValidationReport:
    report = ValidationReport(path=str(path))
    if not path.is_file():
        report.file_errors.append(f"File not found: {path.name}")
        return report
    report.exists = True
    raw = path.read_bytes()
    report.content_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        report.file_errors.append("The file is not valid UTF-8 (save the CSV as 'UTF-8').")
        return report

    reader = csv.DictReader(text.splitlines(keepends=True))
    header = reader.fieldnames or []
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        report.file_errors.append("Missing columns: " + ", ".join(missing))
        return report
    unknown = [c for c in header if c not in COLUMNS]
    if unknown:
        report.file_errors.append("Unknown columns (rename or remove): " + ", ".join(unknown))
    absent = [c for c in LATER_ATTRIBUTE_COLUMNS if c not in header]
    if absent:
        report.notes.append(
            f"Column(s) not found: {', '.join(absent)}. This looks like a file written for vocabulary 1.0; "
            "those attributes count as 'not labelled' in every row."
        )

    seen_ids: set[str] = set()
    groups: dict[str, dict] = {}
    for line_no, raw_row in enumerate(reader, start=2):
        if len(report.rows) >= MAX_ROWS:
            report.file_errors.append(f"More than {MAX_ROWS} rows; split the file.")
            break
        row = {c: (raw_row.get(c) or "").strip() for c in COLUMNS}
        result = RowResult(line=line_no, sample_id=row["sample_id"] or f"(line {line_no})", row=row)
        if not row["sample_id"]:
            result.errors.append("sample_id is empty")
        elif row["sample_id"] in seen_ids:
            result.errors.append("duplicate sample_id")
        seen_ids.add(row["sample_id"])
        _check_row(result, path.parent)

        gid = row["group_id"]
        if gid:  # rows that describe the same face in different languages must carry identical labels
            labels = tuple(row[k] for k in ATTRIBUTE_KEYS)
            group = groups.setdefault(gid, {"labels": labels, "languages": set(), "first": result.sample_id})
            if group["labels"] != labels:
                result.errors.append(f"labels differ from {group['first']} in the same group '{gid}'")
            if row["language"] in group["languages"]:
                result.warnings.append(f"group '{gid}' already has a '{row['language']}' row")
            group["languages"].add(row["language"])
        report.rows.append(result)
    if not report.rows:
        report.file_errors.append("The file has a header but no data rows.")
    return report
