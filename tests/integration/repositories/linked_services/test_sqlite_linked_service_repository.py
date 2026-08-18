"""Integration tests for SqliteLinkedServiceRepository."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import pytest

from src.app.models.linked_service import LinkedService
from src.app.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.app.repositories.linked_services import SqliteLinkedServiceRepository


WorkspaceFactory = Callable[..., Awaitable[None]]


def build_linked_service(service_id: str, name: str, workspace_id: str = 'workspace-1') -> LinkedService:
    """Build a deterministic linked service for repository assertions."""
    timestamp = datetime(2026, 8, 17, tzinfo=UTC)
    return LinkedService(
        id=service_id, workspace_id=workspace_id, name=name, provider_type='openai',
        enabled=True, key_trimmed='sk-te***************', key_ciphertext='encrypted::key',
        key_version=1, base_url='https://api.openai.com/v1', version=1,
        created_at=timestamp, updated_at=timestamp,
    )


@pytest.mark.asyncio
async def test_persists_multiple_services_for_the_same_provider(
    sqlite_database: SqliteDatabase, create_workspace: WorkspaceFactory,
) -> None:
    """Provider type is reusable across independent linked-service rows."""
    await create_workspace(workspace_id='workspace-1')
    repository = SqliteLinkedServiceRepository(sqlite_database)
    first = build_linked_service('service-1', 'primary_openai')
    second = build_linked_service('service-2', 'secondary_openai')

    await repository.create(first)
    await repository.create(second)

    assert await repository.list_for_workspace('workspace-1') == [first, second]


@pytest.mark.asyncio
async def test_get_and_delete_are_workspace_scoped(
    sqlite_database: SqliteDatabase, create_workspace: WorkspaceFactory,
) -> None:
    """A service cannot be read or deleted through another workspace."""
    await create_workspace(workspace_id='workspace-1')
    await create_workspace(workspace_id='workspace-2')
    repository = SqliteLinkedServiceRepository(sqlite_database)
    service = build_linked_service('service-1', 'primary_openai')
    await repository.create(service)

    assert await repository.get('workspace-2', 'service-1') is None
    assert await repository.delete('workspace-2', 'service-1') is False
    assert await repository.get('workspace-1', 'service-1') == service
