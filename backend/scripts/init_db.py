"""Create the database tables (safe to run again - existing tables and data are kept).

    python scripts/init_db.py
    python scripts/init_db.py --reset --yes     # DELETES ALL DATA and recreates empty tables
"""

import _paths  # noqa: F401  (must be first: fixes the import path)
import argparse

from app.core.database import Base, get_engine, init_db
from app.core.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="drop every table first (destroys all data)")
    parser.add_argument("--yes", action="store_true", help="confirm --reset without asking")
    args = parser.parse_args()
    if args.reset:
        if not args.yes and input("This deletes ALL cases, users and sketches records. Type 'delete' to continue: ") != "delete":
            raise SystemExit("Cancelled.")
        from app import models  # noqa: F401

        Base.metadata.drop_all(get_engine())
        print("All tables dropped (image files in storage/sketches are NOT deleted - remove them by hand if you want).")
    init_db()
    print(f"Database ready: {get_settings().effective_database_url}")


if __name__ == "__main__":
    main()
