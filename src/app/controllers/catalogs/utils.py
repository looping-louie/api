"""Shared static catalog controller helpers."""

from src.app.schemas.shared import PositiveInteger


def catalog_version(value: int | None) -> PositiveInteger:
    """Return the required positive version for a packaged definition."""

    if value is None:
        raise ValueError('Packaged catalog definitions require a version.')
    return value