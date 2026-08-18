"""Tests for environment-backed application settings."""

from pathlib import Path

from src.app.services.shared.settings import get_app_settings


def test_get_app_settings_uses_runtime_database_by_default(
    monkeypatch: object,
) -> None:
    """Use the runtime database path when no explicit override is configured."""

    monkeypatch.delenv("LOUIE_DB_PATH", raising=False)
    get_app_settings.cache_clear()

    try:
        settings = get_app_settings()
    finally:
        get_app_settings.cache_clear()

    assert settings.database_path == Path("runtime/db/looping-louie.db")
