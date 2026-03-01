"""Persistence for source-boundary diagnostic artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..jsonio import write_json
from ..paths import PROJECT_ROOT


class DiagnosticStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or PROJECT_ROOT / "data" / "diagnostics"

    def path_for(self, source_type: str, year: int, source_name: str, filename: str) -> Path:
        return self._base_dir / source_type / str(year) / source_name / filename

    def write_json(
        self,
        source_type: str,
        year: int,
        source_name: str,
        filename: str,
        payload: dict[str, Any],
    ) -> Path:
        path = self.path_for(source_type, year, source_name, filename)
        write_json(path, payload)
        return path
