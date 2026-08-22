"""Pure helpers for interpreting provider configuration state."""

from collections.abc import Mapping
from typing import Protocol

from src.app.catalogs.providers import ProviderCatalogEntry, ProviderId
from .errors import ProviderConfigurationError


class ProviderConnection(Protocol):
    """Minimum persisted configuration used by provider helper functions."""

    base_url: str | None
    key_ciphertext: str | None


def clean_optional_value(value: str | None) -> str | None:
    """Trim an optional string and collapse blank input to null."""

    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def find_provider_definition(
    provider_id: str,
    catalog_by_id: Mapping[ProviderId, ProviderCatalogEntry],
) -> ProviderCatalogEntry | None:
    """Return a normalized provider definition when it is catalogued."""

    normalized_provider_id = provider_id.strip().casefold()
    try:
        catalog_id = ProviderId(normalized_provider_id)
    except ValueError:
        return None
    return catalog_by_id.get(catalog_id)


def validate_configuration(
    *,
    definition: ProviderCatalogEntry,
    key_ciphertext: str | None,
    base_url: str | None,
) -> None:
    """Ensure candidate settings satisfy provider requirements."""

    if definition.requires_api_key and key_ciphertext is None:
        raise ProviderConfigurationError(
            provider_id=definition.id.value,
            reason="an API key is required",
        )
    if base_url is None:
        raise ProviderConfigurationError(
            provider_id=definition.id.value,
            reason="a base URL is required",
        )


def resolve_base_url(
    *,
    definition: ProviderCatalogEntry,
    current: ProviderConnection | None,
    supplied: str | None,
    supplied_explicitly: bool,
) -> str | None:
    """Resolve omitted, reset, and custom base URL values."""

    if supplied_explicitly:
        cleaned = clean_optional_value(supplied)
        return (
            cleaned.rstrip("/")
            if cleaned is not None
            else definition.default_base_url
        )
    if current is not None:
        return current.base_url
    return definition.default_base_url


def is_configured(
    *,
    definition: ProviderCatalogEntry,
    credential: ProviderConnection | None,
) -> bool:
    """Return whether stored values satisfy provider requirements."""

    if credential is None or not credential.base_url:
        return False
    if definition.requires_api_key:
        return credential.key_ciphertext is not None
    return True
