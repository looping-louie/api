"""Pure helpers for interpreting provider configuration state."""

from collections.abc import Mapping

from src.app.catalogs.providers import ProviderCatalogEntry, ProviderId
from src.app.models.providers import ProviderCredential, ProviderState

from .provider_errors import ProviderConfigurationError


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
    current: ProviderCredential | None,
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
    credential: ProviderCredential | None,
) -> bool:
    """Return whether stored values satisfy provider requirements."""

    if credential is None or not credential.base_url:
        return False
    if definition.requires_api_key:
        return credential.key_ciphertext is not None
    return True


def build_provider_state(
    *,
    definition: ProviderCatalogEntry,
    credential: ProviderCredential | None,
    model_count: int,
) -> ProviderState:
    """Combine catalog metadata with workspace credential state."""

    configured = is_configured(
        definition=definition,
        credential=credential,
    )
    return ProviderState(
        provider=definition.id.value,
        name=definition.name,
        description=definition.description,
        logo_url=definition.logo_url,
        requires_api_key=definition.requires_api_key,
        configured=configured,
        enabled=bool(credential and credential.enabled and configured),
        key_trimmed=credential.key_trimmed if credential else None,
        base_url=(
            credential.base_url
            if credential is not None
            else definition.default_base_url
        ),
        model_count=model_count,
        model_catalog_note=definition.model_catalog_note,
    )
