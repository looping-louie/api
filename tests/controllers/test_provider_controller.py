"""Tests for ProviderController."""

import pytest

from src.app.controllers.provider import ProviderController
from src.app.schemas.providers import ProviderSetRequest
from tests.fakes.provider_connection_service import (
    FakeProviderConnectionService,
)
from tests.fakes.provider_repository import FakeProviderRepository


@pytest.mark.asyncio
async def test_controller_lists_provider_responses(
    provider_controller: ProviderController,
) -> None:
    response = await provider_controller.list(
        user_id="user-1",
    )

    assert len(response) == 5
    assert response[0].provider == "anthropic"
    assert response[-1].provider == "together"
    assert response[1].model_count == 0
    assert response[1].model_catalog_note is not None
    assert response[2].model_count == 0
    assert response[2].model_catalog_note is not None


@pytest.mark.asyncio
async def test_controller_configures_provider(
    provider_controller: ProviderController,
    provider_repository: FakeProviderRepository,
    provider_connection_service: FakeProviderConnectionService,
) -> None:
    response = await provider_controller.configure(
        user_id="user-1",
        provider_id="openai",
        payload=ProviderSetRequest(
            api_key="sk-test-secret",
            base_url=None,
        ),
    )

    assert response.provider == "openai"
    assert response.configured is True
    assert response.enabled is True
    assert response.key_trimmed == "sk-te***************"

    stored = await provider_repository.get(
        "workspace-1",
        "openai",
    )

    assert stored is not None
    assert stored.key_ciphertext == "encrypted::sk-test-secret"
    assert provider_connection_service.calls


@pytest.mark.asyncio
async def test_controller_deletes_provider(
    provider_controller: ProviderController,
    provider_repository: FakeProviderRepository,
) -> None:
    from tests.factories.providers import build_provider_credential

    provider_repository.seed(
        build_provider_credential(),
    )

    response = await provider_controller.delete(
        user_id="user-1",
        provider_id="openai",
    )

    assert response.deleted is True
    assert await provider_repository.get(
        "workspace-1",
        "openai",
    ) is None
