import io
import time
from pathlib import Path

import pytest
from PIL import Image

from app.core.security import LoginThrottle, hash_password, verify_password
from app.services import storage
from app.services.image_tools import (
    ImageValidationError,
    add_provenance_band,
    inspect_image,
    normalize_to_png,
    thumbnail_png,
)


def png_bytes(size=(64, 64), fmt="PNG", **save) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (90, 100, 110)).save(buf, format=fmt, **save)
    return buf.getvalue()


# ----------------------------------------------------------------------------- images
def test_inspect_accepts_real_images_and_rejects_everything_else():
    assert inspect_image(png_bytes()).format == "PNG"
    for bad, msg in [(b"", "empty"), (b"GIF89a....", "valid image|Only"), (b"<svg xmlns='http://www.w3.org/2000/svg'/>", "valid image|Only"),
                     (png_bytes()[:40], "valid image"), (png_bytes((8, 8)), "too small")]:
        with pytest.raises(ImageValidationError, match=msg):
            inspect_image(bad)
    with pytest.raises(ImageValidationError, match="too many pixels"):
        inspect_image(png_bytes((600, 600)), max_pixels=100_000)
    with pytest.raises(ImageValidationError, match="limit"):
        inspect_image(png_bytes(), max_bytes=10)


def test_normalize_converts_to_clean_rgb_png_and_strips_metadata():
    img = Image.new("RGBA", (100, 80), (255, 0, 0, 0))
    exif = Image.Exif()
    exif[0x010E] = "SECRET-LOCATION-NOTE"
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", exif=exif)
    assert b"SECRET-LOCATION-NOTE" in buf.getvalue()
    clean = normalize_to_png(buf.getvalue())
    assert b"SECRET-LOCATION-NOTE" not in clean and Image.open(io.BytesIO(clean)).format == "PNG"
    big = normalize_to_png(png_bytes((300, 200)), max_side=100)
    assert max(Image.open(io.BytesIO(big)).size) == 100
    transparent = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
    out = io.BytesIO()
    transparent.save(out, format="PNG")
    assert Image.open(io.BytesIO(normalize_to_png(out.getvalue()))).getpixel((5, 5)) == (255, 255, 255)  # flattened onto white


def test_provenance_band_adds_height_and_keeps_width():
    out = Image.open(io.BytesIO(add_provenance_band(png_bytes((1024, 1024)), "SCHEMATIC COMPOSITE - NOT AI-GENERATED", ["Case SA-1 | Version 2", "Preliminary investigative aid."])))
    assert out.size[0] == 1024 and out.size[1] > 1100
    assert thumbnail_png(png_bytes((1024, 1024)), 100) and max(Image.open(io.BytesIO(thumbnail_png(png_bytes((1024, 1024)), 100))).size) == 100


# ----------------------------------------------------------------------------- storage
def test_storage_never_leaves_its_folder(env):
    for evil in ("../secret.txt", "sketches/../../x", "/etc/passwd", "sketches/1/../../../../etc/passwd"):
        with pytest.raises(storage.StorageError):
            storage.resolve(evil)
    rel = storage.save_sketch_png(5, png_bytes())
    assert rel.startswith("sketches/5/") and rel.endswith(".png") and storage.read_bytes(rel) == png_bytes()
    assert storage.save_sketch_png(5, png_bytes()) != rel  # random names: nothing is ever overwritten
    storage.delete_case_files(5)
    with pytest.raises(storage.StorageError):
        storage.read_bytes(rel)


# ----------------------------------------------------------------------------- passwords / throttle
def test_password_hashing_is_salted_and_verifiable():
    h1, h2 = hash_password("correct-horse-9"), hash_password("correct-horse-9")
    assert h1 != h2 and verify_password("correct-horse-9", h1) and not verify_password("wrong", h1) and not verify_password("x", "garbage")


def test_login_throttle_locks_and_releases():
    t = LoginThrottle(max_failures=3, window_seconds=60, lock_seconds=1)
    for _ in range(3):
        t.record_failure("k")
    assert t.retry_after("k") > 0 and t.retry_after("other") == 0
    time.sleep(1.1)
    assert t.retry_after("k") == 0


# ----------------------------------------------------------------------------- headers and serving
def test_security_headers_deny_camera_and_microphone(client):
    h = client.get("/api/health").headers
    assert h["x-content-type-options"] == "nosniff" and h["referrer-policy"] == "no-referrer" and h["cache-control"] == "no-store"
    policy = h["permissions-policy"]
    assert "camera=()" in policy and "microphone=()" in policy and "geolocation=()" in policy


def test_cors_allows_only_configured_origins(client):
    ok = client.options("/api/cases", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options("/api/cases", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers


def test_api_docs_are_served_and_frontend_missing_is_explained(client):
    assert client.get("/docs").status_code == 200 and client.get("/redoc").status_code == 200
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"].startswith("SketchAssist") and "securitySchemes" in spec["components"]
    root = client.get("/").json()
    assert root["code"] == "frontend_not_built"


@pytest.fixture()
def built_frontend(env, monkeypatch):
    dist = Path(env) / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>SketchAssist</title><div id=root></div>", encoding="utf-8")
    (dist / "assets" / "app-abc.js").write_text("console.log(1)", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    (Path(env) / "secret.txt").write_text("top secret", encoding="utf-8")
    monkeypatch.setenv("FRONTEND_DIST_DIR", str(dist))
    from app.core.config import get_settings

    get_settings.cache_clear()
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


def test_spa_routes_fall_back_to_index_with_a_csp_but_api_404s_stay_json(built_frontend):
    page = built_frontend.get("/cases/SA-2026-ABC123/workspace")
    assert page.status_code == 200 and "SketchAssist" in page.text
    csp = page.headers["content-security-policy"]
    assert "default-src 'self'" in csp and "object-src 'none'" in csp and "script-src 'self'" in csp and "img-src 'self' data: blob:" in csp
    assert "frame-ancestors" not in csp  # off unless FRAME_ANCESTORS is set (it would break embedding in previews)
    asset = built_frontend.get("/assets/app-abc.js")
    assert asset.status_code == 200 and "immutable" in asset.headers["cache-control"]
    assert built_frontend.get("/favicon.svg").status_code == 200
    missing = built_frontend.get("/api/does-not-exist")
    assert missing.status_code == 404 and missing.headers["content-type"].startswith("application/json")
    assert "content-security-policy" not in built_frontend.get("/docs").headers  # Swagger UI needs a CDN


def test_static_serving_cannot_read_files_outside_dist(built_frontend):
    for evil in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt", "/..%2fsecret.txt"):
        r = built_frontend.get(evil)
        assert "top secret" not in r.text, evil


def test_frame_ancestors_can_be_enforced(env, monkeypatch, built_frontend):
    monkeypatch.setenv("FRAME_ANCESTORS", "'none'")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import _csp

    assert "frame-ancestors 'none'" in _csp()


# ----------------------------------------------------------------------------- docs
SPEC_ENDPOINTS = [
    ("post", "/api/auth/register"), ("post", "/api/auth/login"), ("get", "/api/cases"), ("post", "/api/cases"), ("get", "/api/cases/{case_id}"),
    ("patch", "/api/cases/{case_id}"), ("delete", "/api/cases/{case_id}"), ("post", "/api/descriptions/parse"), ("post", "/api/sketches/generate"),
    ("post", "/api/sketches/{sketch_id}/revise"), ("get", "/api/sketch-versions"), ("get", "/api/cases/{case_id}/notes"), ("post", "/api/cases/{case_id}/notes"),
    ("get", "/api/datasets/status"), ("post", "/api/datasets/inspect"), ("get", "/api/evaluations"), ("get", "/api/cases/{case_id}/report"),
]  # fmt: skip


def test_every_endpoint_from_the_specification_exists_and_is_documented(client):
    paths = client.get("/openapi.json").json()["paths"]
    for method, path in SPEC_ENDPOINTS:
        assert path in paths and method in paths[path], f"{method.upper()} {path} missing"
        op = paths[path][method]
        assert op.get("summary") and op.get("responses") and op.get("tags"), f"{method.upper()} {path} is not documented"


def test_generated_api_docs_are_not_stale():
    import subprocess
    import sys

    backend = Path(__file__).resolve().parents[1]
    out = subprocess.run([sys.executable, str(backend / "scripts" / "generate_api_docs.py"), "--check"], capture_output=True, text=True, cwd=backend)
    assert out.returncode == 0, out.stdout + out.stderr
