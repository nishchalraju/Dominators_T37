"""Basic application logging: console + rotating file in storage/logs.

Witness descriptions, notes and other case content are never written to the log.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.core.config import get_settings

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def setup_logging() -> None:
    settings = get_settings()
    root = logging.getLogger("sketchassist")
    if getattr(root, "_sketchassist_configured", False):
        return
    root.setLevel(settings.log_level.upper())
    formatter = logging.Formatter(_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    try:
        log_dir = settings.storage_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:  # read-only disk etc. - console logging is enough
        root.warning("Could not create the log file; logging to console only.")

    root.propagate = False
    root._sketchassist_configured = True  # type: ignore[attr-defined]
