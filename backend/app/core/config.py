"""Application settings.

Everything that can differ between machines (secrets, API keys, paths, which AI
provider to use) is read from environment variables or from ``backend/.env``.
Nothing secret is ever hard-coded, and nothing here is sent to the browser.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend
PROJECT_DIR = BACKEND_DIR.parent  # project root (contains package.json)

APP_NAME = "SketchAssist AI"
APP_VERSION = "3.0.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- general ---------------------------------------------------------
    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    secret_key: str = Field(default="", description="Signs login tokens. REQUIRED in production.")
    access_token_expire_minutes: int = 480

    # --- storage ---------------------------------------------------------
    database_url: str = ""  # empty -> SQLite file inside storage_dir
    storage_dir: Path = BACKEND_DIR / "storage"
    datasets_dir: Path = BACKEND_DIR / "datasets"
    frontend_dist_dir: Path = PROJECT_DIR / "dist"

    # --- web -------------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    allow_registration: bool = True
    frame_ancestors: str = ""  # e.g. "'none'" in production to block clickjacking

    # --- uploads / images ------------------------------------------------
    max_upload_mb: int = 5
    max_image_pixels: int = 25_000_000
    stored_image_max_side: int = 2048

    # --- AI provider selection (see docs/MODEL_SELECTION.md) --------------
    ai_provider: Literal["auto", "none", "huggingface", "openai", "diffusers"] = "auto"
    ai_timeout_seconds: int = 180

    # Hugging Face Inference Providers (hosted open-weight models)
    hf_token: str = ""
    hf_provider: str = "auto"
    hf_t2i_model: str = "Qwen/Qwen-Image"
    hf_edit_model: str = "Qwen/Qwen-Image-Edit"

    # OpenAI Images API (or any compatible endpoint)
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_image_model: str = "gpt-image-2.5-sunburst"
    openai_image_quality: str = "medium"

    # Local diffusers inference (needs a large GPU; see requirements-ai-local.txt)
    local_t2i_model: str = "black-forest-labs/FLUX.1-schnell"
    local_edit_model: str = "Qwen/Qwen-Image-Edit"
    local_device: str = "auto"
    local_steps: int = 4

    # --- derived helpers ---------------------------------------------------
    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.storage_dir / 'sketchassist.db').as_posix()}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def resolve_secret_key(self) -> str:
        """Return the signing key.

        In development, if SECRET_KEY is not set, a random key is created once and
        kept in ``storage/.secret_key`` so you are not logged out on every reload.
        In production a missing key is a configuration error.
        """
        if self.secret_key:
            return self.secret_key
        if self.is_production:
            raise RuntimeError("SECRET_KEY must be set when APP_ENV=production.")
        key_file = self.storage_dir / ".secret_key"
        if key_file.exists():
            return key_file.read_text(encoding="utf-8").strip()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        key = secrets.token_urlsafe(48)
        key_file.write_text(key, encoding="utf-8")
        return key


@lru_cache
def get_settings() -> Settings:
    return Settings()
