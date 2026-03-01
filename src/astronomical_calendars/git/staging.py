"""Helpers for staging generated artifacts with git."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..paths import PROJECT_ROOT


class GitStager:
    def __init__(self, repo_root: Path | None = None) -> None:
        self._repo_root = repo_root or PROJECT_ROOT

    def stage_paths(self, paths: list[Path]) -> list[str]:
        normalized = [self._normalize(path) for path in paths]
        if not normalized:
            return []

        subprocess.run(
            ["git", "add", "--", *normalized],
            cwd=self._repo_root,
            check=True,
        )
        return normalized

    def _normalize(self, path: Path) -> str:
        candidate = Path(path)
        if candidate.is_absolute():
            try:
                return str(candidate.relative_to(self._repo_root))
            except ValueError:
                return str(candidate)
        return str(candidate)
