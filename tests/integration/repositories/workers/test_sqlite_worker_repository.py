"""Integration tests for SQLite Worker capability persistence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.app.models.worker import WorkerDocument
from src.app.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.app.repositories.workers.sqlite_repository import SqliteWorkerRepository
from tests.integration.conftest import WorkspaceFactory


@pytest.mark.asyncio
async def test_worker_repository_preserves_harnesses_across_heartbeat(
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    """Worker reads and heartbeats retain the persisted Harness capability set."""

    await create_workspace(workspace_id='workspace-1')
    timestamp = datetime(2026, 8, 24, tzinfo=UTC)
    repository = SqliteWorkerRepository(sqlite_database)
    created = await repository.create(WorkerDocument(
        id='worker-1', workspace_id='workspace-1', registered_at=timestamp,
        last_heartbeat_at=timestamp,
    ))
    fetched = await repository.get(
        workspace_id='workspace-1',
        worker_id='worker-1',
    )
    heartbeated = await repository.heartbeat(
        workspace_id='workspace-1',
        worker_id='worker-1',
        occurred_at=timestamp + timedelta(seconds=1),
    )

    assert fetched == created
    assert heartbeated is not None
    assert heartbeated.harnesses == created.harnesses
    assert heartbeated.last_heartbeat_at > created.last_heartbeat_at
