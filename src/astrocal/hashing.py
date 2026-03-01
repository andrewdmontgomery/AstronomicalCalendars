"""Hash helpers for deterministic content fingerprints."""

from __future__ import annotations

import hashlib


def sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"
