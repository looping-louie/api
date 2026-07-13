"""Tests for ProviderService."""

import pytest

from src.app.services.providers.provider_connection_service import (
    ProviderConnectionError,
)
from src.app.services.providers.provider_service import (
    ProviderConfigurationError,
    ProviderNotConfiguredError,
    ProviderService,
    UnknownProviderError,
)
from tests.factories.providers import build_provider_credential
from tests.fakes.provider_connection_service import (
    FakeProviderConnectionService,
)
from tests.fakes.provider_repository import FakeProviderRepository
from tests.fakes.secret_service import FakeSecretService


@pytest.mark.asyncio
async def test_list_returns_curated_order_and_workspace_state(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
) -> None:
    provider_repository.seed(
        build_provider_credential(),
    )

    providers = await provider_service.list(
        user_id="user-1",
    )

    assert [
        provider.provider
        for provider in providers
    ] == [
        "anthropic",
        "nvidia",
        "ollama",
        "openai",
        "together",
    ]

    openai = next(
        provider
        for provider in providers
        if provider.provider == "openai"
    )

    assert openai.configured is True
    assert openai.enabled is True
    assert openai.model_count == 3
    assert openai.key_trimmed == "sk-te***************"

    anthropic = providers[0]

    assert anthropic.configured is False
    assert anthropic.enabled is False


@pytest.mark.asyncio
async def test_describe_returns_unconfigured_provider_defaults(
    provider_service: ProviderService,
) -> None:
    provider = await provider_service.describe(
        user_id="user-1",
        provider_id="ollama",
    )

    assert provider.provider == "ollama"
    assert provider.configured is False
    assert provider.enabled is False
    assert provider.requires_api_key is False
    assert provider.base_url == "http://localhost:11434"


@pytest.mark.asyncio
async def test_configure_encrypts_tests_and_stores_provider(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
    provider_secret_service: FakeSecretService,
    provider_connection_service: FakeProviderConnectionService,
) -> None:
    provider = await provider_service.configure(
        user_id="user-1",
        provider_id="openai",
        api_key="  sk-test-secret  ",
        base_url=None,
    )

    assert provider.provider == "openai"
    assert provider.configured is True
    assert provider.enabled is True
    assert provider.key_trimmed == "sk-te***************"

    stored = await provider_repository.get(
        "workspace-1",
        "openai",
    )

    assert stored is not None
    assert stored.id == "provider-credential-1"
    assert stored.workspace_id == "workspace-1"
    assert stored.key_ciphertext == "encrypted::sk-test-secret"
    assert stored.key_trimmed == "sk-te***************"
    assert stored.base_url == "https://api.openai.com/v1"

    assert provider_secret_service.encrypted_values == [
        "sk-test-secret",
    ]
    assert provider_connection_service.calls == [
        (
            "openai",
            "sk-test-secret",
            "https://api.openai.com/v1",
        )
    ]


@pytest.mark.asyncio
async def test_reconfigure_preserves_existing_key(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
    provider_secret_service: FakeSecretService,
    provider_connection_service: FakeProviderConnectionService,
) -> None:
    provider_repository.seed(
        build_provider_credential(),
    )

    provider = await provider_service.configure(
        user_id="user-1",
        provider_id="openai",
        api_key=None,
        base_url=" https://openai.internal/v1/ ",
    )

    stored = await provider_repository.get(
        "workspace-1",
        "openai",
    )

    assert stored is not None
    assert stored.id == "credential-1"
    assert stored.key_ciphertext == "encrypted::sk-test-secret"
    assert stored.base_url == "https://openai.internal/v1"
    assert provider.base_url == "https://openai.internal/v1"

    assert provider_secret_service.encrypted_values == []
    assert provider_secret_service.decrypted_values == [
        "encrypted::sk-test-secret",
    ]
    assert provider_connection_service.calls == [
        (
            "openai",
            "sk-test-secret",
            "https://openai.internal/v1",
        )
    ]


@pytest.mark.asyncio
async def test_configure_ollama_without_api_key(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
    provider_connection_service: FakeProviderConnectionService,
) -> None:
    provider = await provider_service.configure(
        user_id="user-1",
        provider_id="ollama",
        api_key=None,
        base_url=None,
    )

    assert provider.configured is True
    assert provider.enabled is True
    assert provider.key_trimmed is None

    stored = await provider_repository.get(
        "workspace-1",
        "ollama",
    )

    assert stored is not None
    assert stored.key_ciphertext is None
    assert stored.base_url == "http://localhost:11434"

    assert provider_connection_service.calls == [
        (
            "ollama",
            None,
            "http://localhost:11434",
        )
    ]


@pytest.mark.asyncio
async def test_configure_rejects_missing_required_api_key(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
    provider_connection_service: FakeProviderConnectionService,
) -> None:
    with pytest.raises(ProviderConfigurationError):
        await provider_service.configure(
            user_id="user-1",
            provider_id="anthropic",
            api_key=None,
            base_url=None,
        )

    assert await provider_repository.get(
        "workspace-1",
        "anthropic",
    ) is None
    assert provider_connection_service.calls == []


@pytest.mark.asyncio
async def test_configure_does_not_store_failed_connection(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
    provider_connection_service: FakeProviderConnectionService,
) -> None:
    provider_connection_service.error = ProviderConnectionError(
        "Provider could not be reached."
    )

    with pytest.raises(ProviderConnectionError):
        await provider_service.configure(
            user_id="user-1",
            provider_id="openai",
            api_key="sk-test-secret",
            base_url=None,
        )

    assert await provider_repository.get(
        "workspace-1",
        "openai",
    ) is None


@pytest.mark.asyncio
async def test_disable_and_enable_preserve_credentials(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
) -> None:
    provider_repository.seed(
        build_provider_credential(),
    )

    disabled = await provider_service.disable(
        user_id="user-1",
        provider_id="openai",
    )

    assert disabled.configured is True
    assert disabled.enabled is False

    stored_disabled = await provider_repository.get(
        "workspace-1",
        "openai",
    )

    assert stored_disabled is not None
    assert stored_disabled.key_ciphertext == "encrypted::sk-test-secret"

    enabled = await provider_service.enable(
        user_id="user-1",
        provider_id="openai",
    )

    assert enabled.configured is True
    assert enabled.enabled is True

    stored_enabled = await provider_repository.get(
        "workspace-1",
        "openai",
    )

    assert stored_enabled is not None
    assert stored_enabled.key_ciphertext == "encrypted::sk-test-secret"


@pytest.mark.asyncio
async def test_enable_rejects_unconfigured_provider(
    provider_service: ProviderService,
) -> None:
    with pytest.raises(ProviderNotConfiguredError):
        await provider_service.enable(
            user_id="user-1",
            provider_id="openai",
        )


@pytest.mark.asyncio
async def test_test_provider_decrypts_stored_key(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
    provider_secret_service: FakeSecretService,
    provider_connection_service: FakeProviderConnectionService,
) -> None:
    provider_repository.seed(
        build_provider_credential(),
    )

    result = await provider_service.test(
        user_id="user-1",
        provider_id="openai",
    )

    assert result.provider == "openai"
    assert result.success is True
    assert result.latency_ms >= 0
    assert provider_secret_service.decrypted_values == [
        "encrypted::sk-test-secret",
    ]
    assert provider_connection_service.calls == [
        (
            "openai",
            "sk-test-secret",
            "https://api.openai.com/v1",
        )
    ]


@pytest.mark.asyncio
async def test_delete_removes_provider_configuration(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
) -> None:
    provider_repository.seed(
        build_provider_credential(),
    )

    await provider_service.delete(
        user_id="user-1",
        provider_id="openai",
    )

    assert await provider_repository.get(
        "workspace-1",
        "openai",
    ) is None
    assert provider_repository.unset_calls[0][0:2] == (
        "workspace-1",
        "openai",
    )


@pytest.mark.asyncio
async def test_unknown_provider_is_rejected(
    provider_service: ProviderService,
) -> None:
    with pytest.raises(UnknownProviderError):
        await provider_service.describe(
            user_id="user-1",
            provider_id="unknown",
        )
