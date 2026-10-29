"""Shared test setup. Every test gets a brand-new database and storage folder, and sees NO secrets."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

@pytest.fixture(autouse=True)
def _clean_global_state():
    """Engine health (last success / error) is process-wide; never let one test see another's."""
    from app.services.sketch_models import base as model_base

    model_base.reset_health()
    yield
    model_base.reset_health()


SECRET_ENV = ("HF_TOKEN", "OPENAI_API_KEY", "DATABASE_URL", "SECRET_KEY")


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Isolated settings: temp DB / storage / datasets, no AI credentials."""
    for key in SECRET_ENV:
        monkeypatch.delenv(key, raising=False)
    datasets = tmp_path / "datasets"
    shutil.copytree(BACKEND / "datasets" / "custom", datasets / "custom")
    (datasets / "external").mkdir(parents=True)
    values = {
        "APP_ENV": "test",
        "SECRET_KEY": "test-secret-key-that-is-long-enough-for-hs256-signing-0123456789",
        "STORAGE_DIR": str(tmp_path / "storage"),
        "DATASETS_DIR": str(datasets),
        "FRONTEND_DIST_DIR": str(tmp_path / "no-dist"),
        "AI_PROVIDER": "auto",
        "HF_TOKEN": "",
        "OPENAI_API_KEY": "",
        "ALLOW_REGISTRATION": "true",
    }
    for k, v in values.items():
        monkeypatch.setenv(k, v)
    from app.api import auth as auth_api
    from app.api import deps
    from app.core.config import get_settings
    from app.core.database import reset_engine
    from app.services.sketch_models import base as model_base
    from app.services.sketch_models.registry import reset_registry

    def reset() -> None:
        get_settings.cache_clear()
        reset_engine()
        reset_registry()
        model_base.reset_health()
        auth_api.login_throttle.reset()
        deps.sketch_limiter.reset()

    reset()
    yield tmp_path
    reset()


@pytest.fixture()
def client(env):
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


from tests.helpers import register  # noqa: E402


@pytest.fixture()
def admin(client):
    """The first registered user is the administrator."""
    data = register(client, "alice")
    assert data["user"]["role"] == "admin"
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.fixture()
def user2(client, admin):
    data = register(client, "bob_second", "another-pass-77")
    assert data["user"]["role"] == "investigator"
    return {"Authorization": f"Bearer {data['access_token']}"}
