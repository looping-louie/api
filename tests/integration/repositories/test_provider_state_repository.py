"""Integration tests for ProviderStateRepositoryAdapter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest

from src.app.catalogs.providers import (
    PROVIDER_CATALOG,
    ProviderId,
)
from src.app.repositories.provider_repository import (
    SqliteProviderRepository,
)
from src.app.repositories.provider_state_repository import (
    ProviderStateRepositoryAdapter,
)
from src.app.repositories.sqlite_database import SqliteDatabase
from tests.integration.factories import build_provider_credential


WorkspaceFactory = Callable[..., Awaitable[None]]


@pytest.mark.asyncio
async def test_returns_configured_and_enabled_provider_state(
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    provider_repository = SqliteProviderRepository(
        sqlite_database,
    )
    adapter = ProviderStateRepositoryAdapter(
        provider_repository=provider_repository,
        catalog=PROVIDER_CATALOG,
    )

    await provider_repository.upsert(
        build_provider_credential(),
    )

    states = await adapter.get_states(
        workspace_id="workspace-1",
        provider_ids=[
            ProviderId.OPENAI,
        ],
    )

    assert states[ProviderId.OPENAI].configured is True
    assert states[ProviderId.OPENAI].enabled is True


@pytest.mark.asyncio
async def test_provider_without_credentials_is_not_configured(
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    provider_repository = SqliteProviderRepository(
        sqlite_database,
    )
    adapter = ProviderStateRepositoryAdapter(
        provider_repository=provider_repository,
        catalog=PROVIDER_CATALOG,
    )

    states = await adapter.get_states(
        workspace_id="workspace-1",
        provider_ids=[
            ProviderId.TOGETHER,
        ],
    )

    assert states[ProviderId.TOGETHER].configured is False
    assert states[ProviderId.TOGETHER].enabled is False


@pytest.mark.asyncio
async def test_ollama_is_configured_without_api_key(
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    provider_repository = SqliteProviderRepository(
        sqlite_database,
    )
    adapter = ProviderStateRepositoryAdapter(
        provider_repository=provider_repository,
        catalog=PROVIDER_CATALOG,
    )

    await provider_repository.upsert(
        build_provider_credential(
            provider="ollama",
            key_trimmed=None,
            key_ciphertext=None,
            base_url="http://localhost:11434",
        )
    )

    states = await adapter.get_states(
        workspace_id="workspace-1",
        provider_ids=[
            ProviderId.OLLAMA,
        ],
    )

    assert states[ProviderId.OLLAMA].configured is True
    assert states[ProviderId.OLLAMA].enabled is True


@pytest.mark.asyncio
async def test_disabled_provider_remains_configured(
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    provider_repository = SqliteProviderRepository(
        sqlite_database,
    )
    adapter = ProviderStateRepositoryAdapter(
        provider_repository=provider_repository,
        catalog=PROVIDER_CATALOG,
    )

    await provider_repository.upsert(
        build_provider_credential(
            enabled=False,
            enabled_by=None,
            enabled_on=None,
        )
    )

    states = await adapter.get_states(
        workspace_id="workspace-1",
        provider_ids=[
            ProviderId.OPENAI,
        ],
    )

    assert states[ProviderId.OPENAI].configured is True
    assert states[ProviderId.OPENAI].enabled is False


@pytest.mark.asyncio
async def test_provider_states_are_isolated_by_workspace(
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    await create_workspace(
        workspace_id="workspace-2",
    )
    provider_repository = SqliteProviderRepository(
        sqlite_database,
    )
    adapter = ProviderStateRepositoryAdapter(
        provider_repository=provider_repository,
        catalog=PROVIDER_CATALOG,
    )

    await provider_repository.upsert(
        build_provider_credential(
            workspace_id="workspace-1",
        )
    )

    states = await adapter.get_states(
        workspace_id="workspace-2",
        provider_ids=[
            ProviderId.OPENAI,
        ],
    )

    assert states[ProviderId.OPENAI].configured is False
    assert states[ProviderId.OPENAI].enabled is False
