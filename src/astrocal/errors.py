"""CLI-facing error types."""

from __future__ import annotations


class CliUserError(ValueError):
    """Expected operator-facing CLI error."""
