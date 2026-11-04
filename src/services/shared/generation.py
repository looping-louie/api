"""Default identifier and timestamp generation for application resources."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def create_identifier() -> str:
    """Create one opaque resource identifier."""

    return uuid4().hex


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""

    return datetime.now(UTC)
