"""SQLite datetime conversion helpers."""

from datetime import datetime


def parse_datetime(value: str) -> datetime:
    """Parse an ISO-8601 datetime persisted by SQLite repositories."""

    return datetime.fromisoformat(value)
