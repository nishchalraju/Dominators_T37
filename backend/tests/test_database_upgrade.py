"""A database made by an earlier version of the app must keep working after an upgrade (no data lost)."""

import sqlite3

import pytest
from sqlalchemy import Column, Integer, Table, inspect

from tests.helpers import register

OLD_CASES_TABLE = """
CREATE TABLE cases (
    id INTEGER NOT NULL PRIMARY KEY, case_id VARCHAR(32) NOT NULL, title VARCHAR(200) NOT NULL, incident_date DATE NOT NULL,
    incident_description TEXT NOT NULL, investigator_ref VARCHAR(64) NOT NULL, status VARCHAR(20) NOT NULL,
    owner_id INTEGER NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL
)
"""  # exactly the columns the table had before investigator_name / witness_name existed
OLD_CASE_ROW = ("INSERT INTO cases VALUES (1, 'SA-2026-OLDCAS', 'Case made before names', '2026-01-02', 'old incident', 'T-1', "
                "'in_progress', 1, '2026-01-02 10:00:00', '2026-01-02 10:00:00')")  # fmt: skip


def make_old_database(settings) -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    path = settings.effective_database_url.removeprefix("sqlite:///")
    with sqlite3.connect(path) as db:
        db.execute(OLD_CASES_TABLE)
        db.execute(OLD_CASE_ROW)


def test_columns_are_added_and_existing_rows_are_kept(env):
    from app.core.config import get_settings
    from app.core.database import add_missing_columns, get_engine, init_db

    make_old_database(get_settings())
    init_db()
    engine = get_engine()
    columns = {c["name"] for c in inspect(engine).get_columns("cases")}
    assert {"investigator_name", "witness_name"} <= columns
    with engine.connect() as conn:
        row = conn.exec_driver_sql("SELECT title, investigator_ref, investigator_name, witness_name FROM cases").one()
    assert tuple(row) == ("Case made before names", "T-1", "", "")  # data kept; names are "not recorded"
    assert add_missing_columns(engine) == []  # running it again changes nothing


def test_the_running_app_opens_an_old_case_and_lets_the_names_be_added(env):
    from fastapi.testclient import TestClient

    from app.core.config import get_settings
    from app.main import create_app

    make_old_database(get_settings())
    with TestClient(create_app()) as client:  # start-up runs the upgrade
        headers = {"Authorization": "Bearer " + register(client)["access_token"]}  # first account = id 1 = the old case's owner
        old = client.get("/api/cases/SA-2026-OLDCAS", headers=headers).json()
        assert old["title"] == "Case made before names" and old["investigator_name"] == "" and old["witness_name"] == ""
        fixed = client.patch("/api/cases/SA-2026-OLDCAS", headers=headers, json={"investigator_name": "Late Entry", "witness_name": "W-01"}).json()
        assert (fixed["investigator_name"], fixed["witness_name"]) == ("Late Entry", "W-01")
        assert client.get("/api/cases/SA-2026-OLDCAS/report", headers=headers).status_code == 200  # the PDF copes with old cases too


def test_a_new_required_column_without_a_default_fails_loudly_instead_of_guessing(env):
    from app.core.database import Base, add_missing_columns, get_engine, init_db

    init_db()
    engine = get_engine()
    probe = Table("upgrade_probe", Base.metadata, Column("id", Integer, primary_key=True), Column("must_have", Integer, nullable=False))
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE TABLE upgrade_probe (id INTEGER PRIMARY KEY)")
        with pytest.raises(RuntimeError, match="cannot be added automatically"):
            add_missing_columns(engine)
    finally:
        Base.metadata.remove(probe)
