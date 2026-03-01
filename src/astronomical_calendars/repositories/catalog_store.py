"""Persistence for accepted catalog records."""

from __future__ import annotations

from pathlib import Path

from ..jsonio import read_json, write_json
from ..models import AcceptedRecord
from ..paths import PROJECT_ROOT


class CatalogStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or PROJECT_ROOT / "data" / "catalog" / "accepted"

    def path_for(self, source_type: str, year: int, source_name: str) -> Path:
        return self._base_dir / source_type / str(year) / f"{source_name}.json"

    def load(self, source_type: str, year: int, source_name: str) -> list[AcceptedRecord]:
        path = self.path_for(source_type, year, source_name)
        if not path.exists():
            return []
        payload = read_json(path)
        return [AcceptedRecord.from_dict(item) for item in payload]

    def save(
        self,
        source_type: str,
        year: int,
        source_name: str,
        records: list[AcceptedRecord],
    ) -> Path:
        path = self.path_for(source_type, year, source_name)
        write_json(path, [record.to_dict() for record in records])
        return path
