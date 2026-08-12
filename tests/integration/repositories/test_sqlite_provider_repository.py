"""Integration tests for SqliteProviderRepository."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import timedelta

import pytest

from src.app.repositories.providers.repository import (
    SqliteProviderRepository,
)
from src.app.repositories.infrastructure.sqlite_database import (
    SqliteDatabase,
)
from tests.integration.factories import build_provider_credential


WorkspaceFactory = Callable[..., Awaitable[None]]


@pytest.mark.asyncio
async def test_upsert_get_and_list_provider(
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    """A stored configuration can be read individually and in a list."""

    await create_workspace(
        workspace_id="workspace-1",
    )
    repository = SqliteProviderRepository(
        sqlite_database,
    )
    credential = build_provider_credential()

    stored = await repository.upsert(
        credential,
    )
    loaded = await repository.get(
        "workspace-1",
        "openai",
    )
    providers = await repository.list_for_workspace(
        "workspace-1",
    )

    assert stored == credential
    assert loaded == credential
    assert providers == [
        credential,
    ]


@pytest.mark.asyncio
async def test_upsert_replaces_provider_configuration(
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    """Upsert replaces mutable provider configuration values."""

    await create_workspace(
        workspace_id="workspace-1",
    )
    repository = SqliteProviderRepository(
        sqlite_database,
    )
    original = build_provider_credential()

    await repository.upsert(
        original,
    )

    updated = replace(
        original,
        base_url="https://openai.internal/v1",
        key_trimmed="sk-ne***************",
        key_ciphertext="encrypted::sk-new-secret",
        updated_at=original.updated_at + timedelta(minutes=5),
    )

    stored = await repository.upsert(
        updated,
    )

    assert stored.id == original.id
    assert stored.base_url == "https://openai.internal/v1"
    assert stored.key_ciphertext == "encrypted::sk-new-secret"


@pytest.mark.asyncio
async def test_repository_isolates_workspaces(
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    """Provider configurations never cross workspace boundaries."""

    await create_workspace(
        workspace_id="workspace-1",
    )
    await create_workspace(
        workspace_id="workspace-2",
    )
    repository = SqliteProviderRepository(
        sqlite_database,
    )

    await repository.upsert(
        build_provider_credential(
            credential_id="credential-1",
            workspace_id="workspace-1",
        )
    )
    await repository.upsert(
        build_provider_credential(
            credential_id="credential-2",
            workspace_id="workspace-2",
        )
    )

    workspace_one = await repository.list_for_workspace(
        "workspace-1",
    )

    assert len(workspace_one) == 1
    assert workspace_one[0].workspace_id == "workspace-1"


@pytest.mark.asyncio
async def test_unset_deletes_provider(
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    """Unset removes the selected workspace provider configuration."""

    await create_workspace(
        workspace_id="workspace-1",
    )
    repository = SqliteProviderRepository(
        sqlite_database,
    )
    credential = build_provider_credential()

    await repository.upsert(
        credential,
    )
    await repository.unset(
        workspace_id="workspace-1",
        provider="openai",
        updated_at=credential.updated_at,
    )

    assert await repository.get(
        "workspace-1",
        "openai",
    ) is None
