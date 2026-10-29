"""Lets every script run as ``python scripts/name.py`` from the backend folder (adds backend/ to the import path)."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
