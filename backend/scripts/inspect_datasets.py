"""Inspect every dataset folder and store the inventory in the database (what the web page shows).

    python scripts/inspect_datasets.py
    python scripts/inspect_datasets.py --dataset cufs
"""

import _paths  # noqa: F401
import argparse

from app.core.database import get_session_factory, init_db
from app.services import datasets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", choices=sorted(datasets.SPECS), help="inspect only this dataset")
    args = parser.parse_args()
    init_db()
    with get_session_factory()() as db:
        for key in [args.dataset] if args.dataset else list(datasets.SPECS):
            out = datasets.inspect_dataset(db, key, None)
            state = "installed" if out.installed else "NOT installed"
            print(f"{key:<18} {state:<14} files/rows: {out.files_found:<6} valid: {out.valid:<6} invalid: {out.invalid}")
            for note in out.notes[:2]:
                print(f"    - {note}")
        db.commit()


if __name__ == "__main__":
    main()
