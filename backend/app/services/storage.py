"""Managed file storage for sketch images.

Files live under ``<storage_dir>/sketches/<case_pk>/<random>.png``. The database stores
only the *relative* path. Paths are always built here - never from user input - and
``resolve`` refuses anything that would escape the storage directory.
"""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from app.core.config import get_settings


class StorageError(RuntimeError):
    pass


def _root() -> Path:
    root = get_settings().storage_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve(relative_path: str) -> Path:
    """Absolute path of a stored file, guaranteed to be inside the storage directory."""
    root = _root()
    candidate = (root / relative_path).resolve()
    if root != candidate and root not in candidate.parents:
        raise StorageError("Refusing to access a path outside the storage directory.")
    return candidate


def save_sketch_png(case_pk: int, data: bytes) -> str:
    """Write a new sketch file (never overwrites: the name is random). Returns the relative path."""
    relative = f"sketches/{int(case_pk)}/{uuid.uuid4().hex}.png"
    target = resolve(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, target)  # atomic: a half-written file is never visible
    return relative


def read_bytes(relative_path: str) -> bytes:
    path = resolve(relative_path)
    if not path.is_file():
        raise StorageError("The stored image file is missing.")
    return path.read_bytes()


def delete_case_files(case_pk: int) -> None:
    folder = resolve(f"sketches/{int(case_pk)}")
    if folder.is_dir():
        shutil.rmtree(folder, ignore_errors=True)
