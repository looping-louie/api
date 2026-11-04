"""Shared fixed-size offset pagination rules."""

from __future__ import annotations


PAGE_SIZE = 10


def require_offset(value: object) -> int:
    """Return a non-negative integer offset or raise ``ValueError``."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("offset must be a non-negative integer")
    return value
