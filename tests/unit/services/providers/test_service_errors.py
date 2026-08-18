"""Failure and deletion tests for the provider service."""

import pytest

from src.app.services.providers.connection import (
    ProviderConnectionError,
)
from src.app.services.providers.errors import UnknownProviderError
from src.app.services.providers.service import ProviderService
from tests.factories.providers import build_provider_credential
from tests.fakes.provider_connection_service import (
    FakeProviderConnectionService,
)
from tests.fakes.provider_repository import FakeProviderRepository
from tests.unit.services.providers.test_service import patch_provider


@pytest.mark.asyncio
async def test_failed_connection_does_not_persist_patch(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
    provider_connection_service: FakeProviderConnectionService,
) -> None:
    """Failed candidate settings never reach persistence."""

    provider_connection_service.error = ProviderConnectionError("Failed.")

    with pytest.raises(ProviderConnectionError):
        await patch_provider(provider_service)

    assert await provider_repository.get("workspace-1", "openai") is None


@pytest.mark.asyncio
async def test_delete_is_idempotent(
    provider_service: ProviderService,
    provider_repository: FakeProviderRepository,
) -> None:
    """Deleting configuration succeeds whether or not it was stored."""

    provider_repository.seed(build_provider_credential())

    await provider_service.delete(
        user_id="user-1",
        provider_id="openai",
    )
    await provider_service.delete(
        user_id="user-1",
        provider_id="openai",
    )

    assert await provider_repository.get("workspace-1", "openai") is None


@pytest.mark.asyncio
async def test_unknown_provider_is_rejected(
    provider_service: ProviderService,
) -> None:
    """Only identifiers from the curated catalog are accepted."""

    with pytest.raises(UnknownProviderError):
        await provider_service.get(
            user_id="user-1",
            provider_id="unknown",
        )
