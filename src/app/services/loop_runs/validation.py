"""Pure input validation for loop-run operations."""

from __future__ import annotations

from src.app.services.loops.types import LoopValidationError


def require_text(value: str, field_name: str) -> str:
    """Return a non-empty normalized string or raise a loop error."""

    normalized = value.strip()
    if not normalized:
        raise LoopValidationError(field_name=field_name, message='must not be empty')
    return normalized
