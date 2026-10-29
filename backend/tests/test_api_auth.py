import jwt
import pytest

from tests.helpers import register


def test_first_user_is_admin_second_is_not(client):
    assert register(client, "alice")["user"]["role"] == "admin"
    assert register(client, "bob_second", "another-pass-77")["user"]["role"] == "investigator"


def test_register_requires_responsible_use_acknowledgement(client):
    r = client.post("/api/auth/register", json={"username": "carol", "password": "correct-horse-9", "acknowledge_responsible_use": False})
    assert r.status_code == 422 and "acknowledge_responsible_use" in r.json()["fields"]


@pytest.mark.parametrize("password", ["short", "aaaaaaaaaaaa", "samename123"])
def test_weak_passwords_are_rejected(client, password):
    username = "samename123"
    r = client.post("/api/auth/register", json={"username": username, "password": password, "acknowledge_responsible_use": True})
    assert r.status_code == 422


def test_duplicate_username_conflicts_case_insensitively(client):
    register(client, "alice")
    r = client.post("/api/auth/register", json={"username": "ALICE", "password": "correct-horse-9", "acknowledge_responsible_use": True})
    assert r.status_code == 409 and r.json()["code"] == "username_taken"


def test_passwords_are_stored_hashed_not_plaintext(client, env):
    register(client, "alice", "correct-horse-9")
    from sqlalchemy import select

    from app.core.database import get_session_factory
    from app.models import User

    with get_session_factory()() as db:
        stored = db.scalar(select(User.password_hash))
    assert "correct-horse-9" not in stored and stored.startswith("scrypt$")


def test_login_success_wrong_password_and_unknown_user_look_alike(client):
    register(client, "alice")
    ok = client.post("/api/auth/login", json={"username": "Alice", "password": "correct-horse-9"})
    assert ok.status_code == 200 and ok.json()["token_type"] == "bearer"
    wrong = client.post("/api/auth/login", json={"username": "alice", "password": "wrong-password-1"})
    unknown = client.post("/api/auth/login", json={"username": "nobody", "password": "wrong-password-1"})
    assert wrong.status_code == unknown.status_code == 401 and wrong.json() == unknown.json()


def test_repeated_failed_logins_are_throttled(client):
    register(client, "alice")
    for _ in range(5):
        client.post("/api/auth/login", json={"username": "alice", "password": "bad-password-1"})
    r = client.post("/api/auth/login", json={"username": "alice", "password": "correct-horse-9"})
    assert r.status_code == 429 and r.json()["code"] == "too_many_attempts" and "retry-after" in r.headers


def test_protected_routes_need_a_valid_token(client, admin):
    assert client.get("/api/cases").status_code == 401
    assert client.get("/api/cases", headers={"Authorization": "Bearer not-a-token"}).status_code == 401
    assert client.get("/api/auth/me", headers=admin).json()["username"] == "alice"


def test_tampered_and_expired_tokens_are_rejected(client, admin):
    token = admin["Authorization"].split()[1]
    forged = jwt.encode({"sub": "1", "exp": 4102444800}, "some-other-secret-key-for-forging-0123456789abcdef", algorithm="HS256")
    expired = jwt.encode({"sub": "1", "exp": 1}, "test-secret-key-that-is-long-enough-for-hs256-signing-0123456789", algorithm="HS256")
    for bad in (forged, expired, token[:-3] + "abc"):
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad}"})
        assert r.status_code == 401 and r.json()["code"] == "invalid_token"


def test_registration_can_be_switched_off(client, monkeypatch):
    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    r = client.post("/api/auth/register", json={"username": "dave", "password": "correct-horse-9", "acknowledge_responsible_use": True})
    assert r.status_code == 403 and r.json()["code"] == "registration_disabled"
