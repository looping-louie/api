"""Integration tests for SQLite Worker capability persistence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.app.models.worker import WorkerDocument, WorkerHarnessCapability
from src.app.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.app.repositories.workers.sqlite_repository import SqliteWorkerRepository
from tests.integration.conftest import WorkspaceFactory


@pytest.mark.asyncio
async def test_worker_repository_preserves_harnesses_across_heartbeat(
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    """Worker reads and heartbeats retain the persisted Harness capability set."""

    await create_workspace(project_id='workspace-1')
    timestamp = datetime(2026, 8, 24, tzinfo=UTC)
    repository = SqliteWorkerRepository(sqlite_database)
    created = await repository.create(WorkerDocument(
        id='worker-1', project_id='workspace-1', registered_at=timestamp,
        last_heartbeat_at=timestamp,
        harnesses=(WorkerHarnessCapability(kind='louie'),),
    ))
    fetched = await repository.get(
        project_id='workspace-1',
        worker_id='worker-1',
    )
    heartbeated = await repository.heartbeat(
        project_id='workspace-1',
        worker_id='worker-1',
        occurred_at=timestamp + timedelta(seconds=1),
    )

    assert fetched == created
    assert heartbeated is not None
    assert heartbeated.harnesses == created.harnesses
    assert heartbeated.last_heartbeat_at > created.last_heartbeat_at


@pytest.mark.asyncio
async def test_worker_repository_heartbeat_replaces_harnesses(
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    """The latest observed Harness set replaces stale registration capabilities."""

    await create_workspace(project_id='workspace-1')
    timestamp = datetime(2026, 8, 24, tzinfo=UTC)
    repository = SqliteWorkerRepository(sqlite_database)
    await repository.create(WorkerDocument(
        id='worker-1', project_id='workspace-1', registered_at=timestamp,
        last_heartbeat_at=timestamp,
        harnesses=(
            WorkerHarnessCapability(kind='louie'),
            WorkerHarnessCapability(kind='codex_cli'),
        ),
    ))

    heartbeated = await repository.heartbeat(
        project_id='workspace-1',
        worker_id='worker-1',
        occurred_at=timestamp + timedelta(seconds=1),
        harnesses=(WorkerHarnessCapability(kind='louie'),),
    )

    assert heartbeated is not None
    assert [harness.kind for harness in heartbeated.harnesses] == ['louie']


@pytest.mark.asyncio
async def test_worker_repository_summarizes_active_harness_compatibility(
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    """Readiness distinguishes registered, active, and compatible Workers."""

    await create_workspace(project_id='workspace-1')
    timestamp = datetime(2026, 8, 24, tzinfo=UTC)
    repository = SqliteWorkerRepository(sqlite_database)
    await repository.create(WorkerDocument(
        id='stale-codex', project_id='workspace-1', registered_at=timestamp,
        last_heartbeat_at=timestamp,
        harnesses=(WorkerHarnessCapability(kind='codex_cli'),),
    ))
    await repository.create(WorkerDocument(
        id='active-louie', project_id='workspace-1', registered_at=timestamp,
        last_heartbeat_at=timestamp + timedelta(minutes=3),
        harnesses=(WorkerHarnessCapability(kind='louie'),),
    ))
    await repository.create(WorkerDocument(
        id='active-codex', project_id='workspace-1', registered_at=timestamp,
        last_heartbeat_at=timestamp + timedelta(minutes=4),
        harnesses=(WorkerHarnessCapability(kind='codex_cli'),),
    ))

    readiness = await repository.readiness(
        project_id='workspace-1',
        active_since=timestamp + timedelta(minutes=2),
        harness={'kind': 'codex_cli', 'version': 'v1', 'config': {}},
    )

    assert readiness.registered_worker_count == 3
    assert readiness.active_worker_count == 2
    assert readiness.compatible_worker_count == 1
    assert readiness.latest_heartbeat_at == timestamp + timedelta(minutes=4)
