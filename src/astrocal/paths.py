"""Filesystem path helpers."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(
    os.environ.get("ASTROCAL_PROJECT_ROOT", str(Path(__file__).resolve().parents[2]))
).resolve()
