"""Persistence for normalized candidate records."""

from __future__ import annotations

from pathlib import Path

from ..jsonio import read_json, write_json
from ..models import CandidateRecord
from ..paths import PROJECT_ROOT


class CandidateStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or PROJECT_ROOT / "data" / "normalized"

    def path_for(self, source_type: str, year: int, source_name: str) -> Path:
        return self._base_dir / source_type / str(year) / f"{source_name}.json"

    def load(self, source_type: str, year: int, source_name: str) -> list[CandidateRecord]:
        path = self.path_for(source_type, year, source_name)
        if not path.exists():
            return []
        payload = read_json(path)
        return [CandidateRecord.from_dict(item) for item in payload]

    def save(
        self,
        source_type: str,
        year: int,
        source_name: str,
        candidates: list[CandidateRecord],
    ) -> Path:
        path = self.path_for(source_type, year, source_name)
        write_json(path, [candidate.to_dict() for candidate in candidates])
        return path
