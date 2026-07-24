"""Tests for the provider controller."""

import pytest

from src.app.controllers.provider import ProviderController
from src.app.schemas.providers import ProviderPatchRequest
from tests.fakes.provider_repository import FakeProviderRepository


@pytest.mark.asyncio
async def test_controller_lists_provider_responses(
    provider_controller: ProviderController,
) -> None:
    """The controller converts every catalog entry to an HTTP response."""

    response = await provider_controller.list(user_id="user-1")

    assert len(response) == 5
    assert response[0].provider == "anthropic"
    assert response[-1].provider == "together"


@pytest.mark.asyncio
async def test_controller_gets_provider(
    provider_controller: ProviderController,
) -> None:
    """The controller returns catalog state for one provider."""

    response = await provider_controller.get(
        user_id="user-1",
        provider_id="ollama",
    )

    assert response.provider == "ollama"
    assert response.requires_api_key is False


@pytest.mark.asyncio
async def test_controller_patches_provider(
    provider_controller: ProviderController,
    provider_repository: FakeProviderRepository,
) -> None:
    """The controller forwards supplied patch fields to the service."""

    response = await provider_controller.patch(
        user_id="user-1",
        provider_id="openai",
        payload=ProviderPatchRequest(api_key="sk-test-secret"),
    )

    assert response.configured is True
    assert response.enabled is True
    assert response.key_trimmed == "sk-te***************"

    stored = await provider_repository.get("workspace-1", "openai")
    assert stored is not None
    assert stored.key_ciphertext == "encrypted::sk-test-secret"


@pytest.mark.asyncio
async def test_controller_deletes_provider_configuration(
    provider_controller: ProviderController,
    provider_repository: FakeProviderRepository,
) -> None:
    """The controller returns the standard deletion response."""

    from tests.factories.providers import build_provider_credential

    provider_repository.seed(build_provider_credential())

    response = await provider_controller.delete(
        user_id="user-1",
        provider_id="openai",
    )

    assert response.deleted is True
    assert await provider_repository.get("workspace-1", "openai") is None
