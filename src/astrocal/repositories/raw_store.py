"""Persistence for raw source artifacts."""

from __future__ import annotations

from pathlib import Path

from ..paths import PROJECT_ROOT


class RawStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or PROJECT_ROOT / "data" / "raw"

    def dir_for(self, source_type: str, year: int, source_name: str) -> Path:
        return self._base_dir / source_type / str(year) / source_name

    def write_text(
        self,
        source_type: str,
        year: int,
        source_name: str,
        filename: str,
        content: str,
    ) -> Path:
        path = self.dir_for(source_type, year, source_name) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_bytes(
        self,
        source_type: str,
        year: int,
        source_name: str,
        filename: str,
        content: bytes,
    ) -> Path:
        path = self.dir_for(source_type, year, source_name) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path
