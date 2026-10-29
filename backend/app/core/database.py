"""Database engine and session handling (SQLAlchemy 2.0, SQLite by default)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime, timezone

from sqlalchemy import DateTime, Engine, create_engine, event, inspect
from sqlalchemy.schema import CreateColumn
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.core.config import get_settings

log = logging.getLogger("sketchassist.db")


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class UTCDateTime(TypeDecorator):
    """Stores UTC datetimes and always returns timezone-aware UTC values.

    SQLite has no real timezone support, so plain DateTime columns come back
    "naive". That would make the browser treat server times as local time.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):  # noqa: ANN001
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect):  # noqa: ANN001
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _configure_sqlite(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_connection, _record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")  # enforce relationships
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


def get_engine() -> Engine:
    global _engine, _session_factory
    if _engine is None:
        url = get_settings().effective_database_url
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
        if url.startswith("sqlite"):
            _configure_sqlite(_engine)
        _session_factory = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
        log.info("Database engine created for %s", _engine.url.render_as_string(hide_password=True))
    return _engine


def reset_engine() -> None:
    """Forget the cached engine (used by tests and by `scripts/init_db.py --reset`)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def add_missing_columns(engine: Engine) -> list[str]:
    """Bring an existing database up to date by ADDING columns that newer code expects.

    ``create_all`` creates missing tables but never touches existing ones, so a database made by an older
    version of the app would otherwise break the moment a model gains a column. This handles only the safe,
    additive case (a new column that is nullable or has a default); nothing is dropped, renamed or rewritten,
    and existing rows keep their data. Anything else needs a real migration, so it fails loudly instead.
    Returns the ``table.column`` names that were added.
    """
    added: list[str] = []
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue  # create_all makes it complete
            present = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in present:
                    continue
                if column.primary_key or (not column.nullable and column.server_default is None):
                    raise RuntimeError(
                        f"The database table '{table.name}' lacks the column '{column.name}', which cannot be added "
                        "automatically. During development you can delete storage/sketchassist.db to start fresh."
                    )
                fragment = str(CreateColumn(column).compile(dialect=engine.dialect))
                conn.exec_driver_sql(f"ALTER TABLE {engine.dialect.identifier_preparer.quote(table.name)} ADD COLUMN {fragment}")
                added.append(f"{table.name}.{column.name}")
                log.info("Database upgrade: added column %s.%s", table.name, column.name)
    return added


def init_db() -> None:
    """Create all tables (idempotent) and add columns an older database is missing. Importing the models registers them."""
    from app import models  # noqa: F401  (side effect: registers tables)

    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    Base.metadata.create_all(engine)
    add_missing_columns(engine)
