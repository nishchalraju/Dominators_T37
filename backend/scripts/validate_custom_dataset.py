"""Check a custom dataset CSV against the controlled vocabulary and the format rules.

    python scripts/validate_custom_dataset.py                       # checks datasets/custom/attribute_samples.csv
    python scripts/validate_custom_dataset.py path/to/your.csv

Exit code 0 = valid, 1 = problems found (each one names the row and the reason).
"""

import _paths  # noqa: F401
import argparse
from pathlib import Path

from app.core.config import get_settings
from app.services import custom_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", nargs="?", type=Path, default=get_settings().datasets_dir / "custom" / custom_dataset.CSV_NAME)
    args = parser.parse_args()
    report = custom_dataset.validate_file(args.csv)

    print(f"File: {args.csv}")
    for err in report.file_errors:
        print(f"  FILE ERROR: {err}")
    for note in report.notes:
        print(f"  note: {note}")
    bad = [r for r in report.rows if not r.valid]
    for r in bad:
        for err in r.errors:
            print(f"  line {r.line} ({r.sample_id}): {err}")
    warned = [r for r in report.rows if r.warnings and r.valid]
    for r in warned[:20]:
        print(f"  note line {r.line} ({r.sample_id}): {'; '.join(r.warnings)}")
    print(f"Rows: {report.total}  valid: {len(report.valid_rows)}  invalid: {len(bad)}")
    if report.rows:
        print("Languages:", report.counts("language"), "| splits:", report.counts("split"))
        print("Translation review status:", report.counts("translation_review_status"))
    if report.ok:
        print("RESULT: valid")
        return 0
    print("RESULT: INVALID")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
