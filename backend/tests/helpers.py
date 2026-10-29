"""Small helpers shared by the API tests."""

from __future__ import annotations


def register(client, username: str = "alice", password: str = "correct-horse-9") -> dict:
    r = client.post("/api/auth/register", json={"username": username, "password": password, "acknowledge_responsible_use": True})
    assert r.status_code == 201, r.text
    return r.json()


def make_case(client, headers, **overrides) -> dict:
    body = {
        "title": "Synthetic test case", "incident_date": "2026-10-20", "investigator_ref": "T-100", "incident_description": "synthetic",
        "investigator_name": "Test Investigator", "witness_name": "Test Witness",  # invented names
    }
    body.update(overrides)
    r = client.post("/api/cases", headers=headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


ATTRS = {
    "apparent_gender": "male", "age_description": "adult", "face_shape": "round", "hair_length": "short",
    "hair_style": "curly", "eyebrows": "medium", "nose_shape": "narrow", "facial_hair": "none", "glasses": "none",
}  # fmt: skip


def generate(client, headers, case_id: str, attributes: dict | None = None, engine: str = "schematic"):
    return client.post("/api/sketches/generate", headers=headers, json={"case_id": case_id, "attributes": attributes or ATTRS, "engine": engine})
