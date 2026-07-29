"""Tests for workspace provider configuration behavior."""

import pytest

from src.app.catalogs.providers import ProviderCatalogEntry, ProviderId
from src.app.models.providers import ProviderState
from src.app.services.providers.errors import ProviderConfigurationError
from src.app.services.providers.service import ProviderService
from src.app.services.shared.tenant import TenantService
from tests.factories.providers import build_provider_credential
from tests.fakes.model_registry_service import FakeModelRegistryService
from tests.fakes.provider_connection_service import (
    FakeProviderConnectionService,
)
from tests.fakes.provider_repository import FakeProviderRepository
from tests.fakes.secret_service import FakeSecretService


async def patch_provider(
    service: ProviderService,
    *,
    provider_id: str = "openai",
    api_key: str | None = "sk-test-secret",
    api_key_supplied: bool = True,
    base_url: str | None = None,
    base_url_supplied: bool = False,
    enabled: bool | None = None,
) -> ProviderState:
    """Patch a provider using concise defaults for service tests."""

    return await service.patch(
        user_id="user-1",
        provider_id=provider_id,
        api_key=api_key,
        api_key_supplied=api_key_supplied,
        base_url=base_url,
        base_url_supplied=base_url_supplied,
        enabled=enabled,
    )


@pytest.mark.asyncio
async def test_list_returns_catalog_order_and_workspace_state(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
) -> None:
    """Listing merges ordered catalog metadata with stored state."""

    provider_repository.seed(build_provider_credential())

    providers = await provider_service.list(user_id="user-1")

    assert [provider.provider for provider in providers] == [
        "anthropic",
        "nvidia",
        "ollama",
        "openai",
        "together",
    ]
    openai = next(item for item in providers if item.provider == "openai")
    assert openai.configured is True
    assert openai.enabled is True
    assert openai.model_count == 3


@pytest.mark.asyncio
async def test_list_uses_injected_catalog(
    provider_repository: FakeProviderRepository,
    tenant_service: TenantService,
    provider_secret_service: FakeSecretService,
    provider_connection_service: FakeProviderConnectionService,
) -> None:
    """The service does not permit providers outside its injected catalog."""

    service = ProviderService(
        repository=provider_repository,
        tenant_service=tenant_service,
        secret_service=provider_secret_service,
        connection_service=provider_connection_service,
        model_registry=FakeModelRegistryService(),
        catalog=(
            ProviderCatalogEntry(
                id=ProviderId.OLLAMA,
                name="Injected Ollama",
                description="Injected provider.",
                logo_url="/ollama.svg",
                requires_api_key=False,
                default_base_url="http://ollama.internal",
            ),
        ),
    )

    providers = await service.list(user_id="user-1")

    assert len(providers) == 1
    assert providers[0].name == "Injected Ollama"


@pytest.mark.asyncio
async def test_get_returns_unconfigured_catalog_defaults(
    provider_service: ProviderService,
) -> None:
    """Getting an unconfigured provider returns its catalog defaults."""

    provider = await provider_service.get(
        user_id="user-1",
        provider_id="ollama",
    )

    assert provider.configured is False
    assert provider.enabled is False
    assert provider.base_url == "http://localhost:11434"


@pytest.mark.asyncio
async def test_patch_initial_configuration_encrypts_tests_and_enables(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
    provider_secret_service: FakeSecretService,
    provider_connection_service: FakeProviderConnectionService,
) -> None:
    """Initial configuration is encrypted, tested, stored, and enabled."""

    provider = await patch_provider(
        provider_service,
        api_key="  sk-test-secret  ",
    )

    stored = await provider_repository.get("workspace-1", "openai")
    assert provider.configured is True
    assert provider.enabled is True
    assert stored is not None
    assert stored.key_ciphertext == "encrypted::sk-test-secret"
    assert stored.base_url == "https://api.openai.com/v1"
    assert provider_secret_service.encrypted_values == ["sk-test-secret"]
    assert provider_connection_service.calls == [
        ("openai", "sk-test-secret", "https://api.openai.com/v1")
    ]


@pytest.mark.asyncio
async def test_patch_omitted_fields_preserves_key_and_enabled_state(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
) -> None:
    """Partial configuration updates preserve every omitted field."""

    provider_repository.seed(build_provider_credential(enabled=False))

    provider = await patch_provider(
        provider_service,
        api_key=None,
        api_key_supplied=False,
        base_url=" https://openai.internal/v1/ ",
        base_url_supplied=True,
    )

    stored = await provider_repository.get("workspace-1", "openai")
    assert stored is not None
    assert stored.key_ciphertext == "encrypted::sk-test-secret"
    assert stored.base_url == "https://openai.internal/v1"
    assert provider.enabled is False


@pytest.mark.asyncio
async def test_patch_can_disable_without_testing_connection(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
    provider_connection_service: FakeProviderConnectionService,
) -> None:
    """Disabling preserves credentials and avoids an external connection."""

    provider_repository.seed(build_provider_credential())

    provider = await patch_provider(
        provider_service,
        api_key=None,
        api_key_supplied=False,
        enabled=False,
    )

    stored = await provider_repository.get("workspace-1", "openai")
    assert provider.enabled is False
    assert stored is not None
    assert stored.key_ciphertext == "encrypted::sk-test-secret"
    assert provider_connection_service.calls == []


@pytest.mark.asyncio
async def test_patch_reenabling_tests_stored_configuration(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
    provider_secret_service: FakeSecretService,
    provider_connection_service: FakeProviderConnectionService,
) -> None:
    """Re-enabling decrypts and tests the stored credentials."""

    provider_repository.seed(build_provider_credential(enabled=False))

    provider = await patch_provider(
        provider_service,
        api_key=None,
        api_key_supplied=False,
        enabled=True,
    )

    assert provider.enabled is True
    assert provider_secret_service.decrypted_values == [
        "encrypted::sk-test-secret"
    ]
    assert provider_connection_service.calls == [
        ("openai", "sk-test-secret", "https://api.openai.com/v1")
    ]


@pytest.mark.asyncio
async def test_patch_ollama_uses_default_without_api_key(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
) -> None:
    """A keyless catalog provider can be configured from its defaults."""

    provider = await patch_provider(
        provider_service,
        provider_id="ollama",
        api_key=None,
        api_key_supplied=False,
        enabled=True,
    )

    stored = await provider_repository.get("workspace-1", "ollama")
    assert provider.configured is True
    assert stored is not None
    assert stored.base_url == "http://localhost:11434"


@pytest.mark.asyncio
async def test_patch_rejects_clearing_required_api_key(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
) -> None:
    """Required provider keys cannot be explicitly cleared."""

    provider_repository.seed(build_provider_credential())

    with pytest.raises(ProviderConfigurationError):
        await patch_provider(provider_service, api_key=None)

    stored = await provider_repository.get("workspace-1", "openai")
    assert stored is not None
    assert stored.key_ciphertext == "encrypted::sk-test-secret"


@pytest.mark.asyncio
async def test_patch_null_base_url_restores_catalog_default(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
) -> None:
    """An explicit null base URL restores the catalog default."""

    provider_repository.seed(
        build_provider_credential(base_url="https://openai.internal/v1")
    )

    provider = await patch_provider(
        provider_service,
        api_key=None,
        api_key_supplied=False,
        base_url=None,
        base_url_supplied=True,
    )

    assert provider.base_url == "https://api.openai.com/v1"
