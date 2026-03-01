"""Persistence for ICS sequence state."""

from __future__ import annotations

from pathlib import Path

from ..jsonio import read_json, write_json
from ..paths import PROJECT_ROOT


class SequenceStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or PROJECT_ROOT / "data" / "state" / "sequences"

    def path_for(self, calendar_name: str) -> Path:
        return self._base_dir / f"{calendar_name}.json"

    def load(self, calendar_name: str) -> dict[str, int]:
        path = self.path_for(calendar_name)
        if not path.exists():
            return {}
        payload = read_json(path)
        return {key: int(value) for key, value in payload.items()}

    def save(self, calendar_name: str, sequence_map: dict[str, int]) -> Path:
        path = self.path_for(calendar_name)
        write_json(path, sequence_map)
        return path
