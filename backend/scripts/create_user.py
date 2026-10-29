"""Create (or promote) a user from the command line - handy for the first administrator.

    python scripts/create_user.py --username alice --admin
"""

import _paths  # noqa: F401
import argparse
import getpass

from sqlalchemy import select

from app.core.database import get_session_factory, init_db, utcnow
from app.core.security import hash_password
from app.models import User
from app.schemas.auth import USERNAME_RE


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--username", required=True)
    parser.add_argument("--admin", action="store_true", help="give the user the administrator role")
    args = parser.parse_args()
    username = args.username.strip().lower()
    if not USERNAME_RE.match(username):
        raise SystemExit("Username must be 3-32 characters: letters, digits, underscore, dot or hyphen.")
    init_db()
    with get_session_factory()() as db:
        user = db.scalar(select(User).where(User.username == username))
        if user:
            if args.admin and user.role != "admin":
                user.role = "admin"
                db.commit()
                print(f"'{username}' is now an administrator.")
            else:
                print(f"'{username}' already exists; nothing changed.")
            return
        password = getpass.getpass("Password (at least 10 characters, hidden): ")
        if len(password) < 10 or password != getpass.getpass("Repeat password: "):
            raise SystemExit("Passwords must match and be at least 10 characters.")
        db.add(User(username=username, display_name=username, password_hash=hash_password(password),
                    role="admin" if args.admin else "investigator", responsible_use_ack_at=utcnow()))  # fmt: skip
        db.commit()
        print(f"Created {'administrator' if args.admin else 'investigator'} '{username}'.")


if __name__ == "__main__":
    main()
