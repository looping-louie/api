"""HTTP controllers for model provider configuration."""

from typing import NoReturn

from fastapi import HTTPException, status

from src.app.repositories.provider_repository import (
    SqliteProviderRepository,
)
from src.app.schemas.providers import (
    ProviderEnabledRequest,
    ProviderResponse,
    ProviderSetRequest,
    ProviderTestResponse,
)
from src.app.services.providers.model_registry_service import (
    StaticModelRegistryService,
)
from src.app.services.providers.provider_connection_service import (
    HttpProviderConnectionService,
    ProviderConnectionError,
)
from src.app.services.providers.provider_service import (
    ProviderConfigurationError,
    ProviderNotConfiguredError,
    ProviderService,
    UnknownProviderError,
)
from src.app.services.providers.provider_settings_service import (
    get_provider_settings,
)
from src.app.services.providers.request_context_service import (
    EnvironmentRequestContextService,
)
from src.app.services.providers.secret_service import FernetSecretService


def build_provider_service() -> ProviderService:
    """Build ProviderService with concrete infrastructure dependencies."""

    settings = get_provider_settings()

    return ProviderService(
        repository=SqliteProviderRepository(
            database_path=settings.database_path
        ),
        secret_service=FernetSecretService(
            encryption_key=settings.encryption_key
        ),
        connection_service=HttpProviderConnectionService(),
        model_registry=StaticModelRegistryService(
            counts=settings.model_counts
        ),
        request_context=EnvironmentRequestContextService(
            org_id=settings.org_id,
            user_id=settings.user_id,
        ),
    )


_provider_service = build_provider_service()


async def list_providers() -> list[ProviderResponse]:
    """Return all providers and their safe configuration state."""

    providers = await _provider_service.list_providers()

    return [
        ProviderResponse.model_validate(provider)
        for provider in providers
    ]


async def set_provider(
    provider: str,
    request: ProviderSetRequest,
) -> ProviderResponse:
    """Create or replace provider configuration."""

    try:
        configured = await _provider_service.set_provider(
            provider=provider,
            api_key=request.api_key,
            base_url=request.base_url,
        )
    except (
        UnknownProviderError,
        ProviderConfigurationError,
        ProviderConnectionError,
    ) as exc:
        _raise_http_error(exc)

    return ProviderResponse.model_validate(configured)


async def set_provider_enabled(
    provider: str,
    request: ProviderEnabledRequest,
) -> ProviderResponse:
    """Enable or disable provider configuration."""

    try:
        configured = await _provider_service.set_provider_enabled(
            provider=provider,
            enabled=request.enabled,
        )
    except (
        UnknownProviderError,
        ProviderConfigurationError,
        ProviderNotConfiguredError,
    ) as exc:
        _raise_http_error(exc)

    return ProviderResponse.model_validate(configured)


async def unset_provider(provider: str) -> None:
    """Delete provider configuration and encrypted credentials."""

    try:
        await _provider_service.unset_provider(provider=provider)
    except UnknownProviderError as exc:
        _raise_http_error(exc)


async def test_provider(
    provider: str,
) -> ProviderTestResponse:
    """Test stored provider configuration."""

    try:
        result = await _provider_service.test_provider(
            provider=provider
        )
    except (
        UnknownProviderError,
        ProviderConfigurationError,
        ProviderNotConfiguredError,
        ProviderConnectionError,
    ) as exc:
        _raise_http_error(exc)

    return ProviderTestResponse.model_validate(result)


def _raise_http_error(exc: Exception) -> NoReturn:
    """Map domain and integration errors to safe HTTP responses."""

    if isinstance(exc, UnknownProviderError):
        code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ProviderNotConfiguredError):
        code = status.HTTP_409_CONFLICT
    elif isinstance(exc, ProviderConnectionError):
        code = status.HTTP_502_BAD_GATEWAY
    else:
        code = status.HTTP_400_BAD_REQUEST

    raise HTTPException(
        status_code=code,
        detail=str(exc),
    ) from exc
