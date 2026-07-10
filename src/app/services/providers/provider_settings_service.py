"""Backward-compatible provider settings imports."""

from src.app.services.app_settings_service import (
    AppSettings,
    get_app_settings,
)


ProviderSettings = AppSettings
get_provider_settings = get_app_settings

__all__ = [
    "ProviderSettings",
    "get_provider_settings",
]
