"""Persistence for validation, reconciliation, and build reports."""

from __future__ import annotations

from pathlib import Path

from ..jsonio import write_json
from ..paths import PROJECT_ROOT


class ReportStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or PROJECT_ROOT / "data" / "catalog" / "reports"

    def run_dir(self, run_timestamp: str) -> Path:
        return self._base_dir / run_timestamp

    def write_json_report(self, run_timestamp: str, name: str, payload: dict) -> Path:
        path = self.run_dir(run_timestamp) / f"{name}.json"
        write_json(path, payload)
        return path
