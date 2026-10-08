"""Integration tests for SQLite Worker persistence."""

from datetime import UTC, datetime, timedelta

import pytest

from src.app.models.worker import WorkerHarnessCapability
from src.app.models.worker_instance import (
    WorkerInstanceDocument,
    WorkerInstanceProjectDocument,
    WorkerProjectEnablementDocument,
)
from src.app.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.app.repositories.worker_instances import SqliteWorkerInstanceRepository
from tests.integration.conftest import WorkspaceFactory


@pytest.mark.asyncio
async def test_worker_can_be_enabled_for_multiple_projects(
    sqlite_database: SqliteDatabase,
    create_workspace: WorkspaceFactory,
) -> None:
    """A Worker has explicit execution permissions per Project."""

    await create_workspace(
        project_id='project-a',
        memberships=(('user-1', 'owner', True),),
    )
    await create_workspace(
        project_id='project-b',
        memberships=(('user-1', 'owner', False),),
    )
    timestamp = datetime(2026, 10, 6, tzinfo=UTC)
    repository = SqliteWorkerInstanceRepository(sqlite_database)
    worker = WorkerInstanceDocument(
        id='worker-1',
        owner_user_id='user-1',
        registered_at=timestamp,
        last_heartbeat_at=timestamp,
        harnesses=(WorkerHarnessCapability(kind='codex_cli'),),
    )
    await repository.create(worker)
    assert await repository.get(worker_instance_id=worker.id) == worker
    heartbeated = await repository.heartbeat(
        worker_instance_id=worker.id,
        occurred_at=timestamp + timedelta(seconds=1),
        harnesses=(),
    )

    assert heartbeated is not None
    assert heartbeated.harnesses == ()
    assert heartbeated.last_heartbeat_at > worker.last_heartbeat_at

    enabled_for_a = await repository.enable_project(
        WorkerProjectEnablementDocument(
            worker_instance_id=worker.id,
            project_id='project-a',
            enabled_at=timestamp,
        ),
    )
    enabled_for_b = await repository.enable_project(
        WorkerProjectEnablementDocument(
            worker_instance_id=worker.id,
            project_id='project-b',
            enabled_at=timestamp,
        ),
    )
    repeated_enablement = await repository.enable_project(
        WorkerProjectEnablementDocument(
            worker_instance_id=worker.id,
            project_id='project-a',
            enabled_at=timestamp + timedelta(seconds=2),
        ),
    )

    assert await repository.get_enabled(
        worker_instance_id=worker.id,
        project_id='project-a',
    ) == heartbeated
    assert await repository.get_enabled(
        worker_instance_id=worker.id,
        project_id='project-missing',
    ) is None
    assert await repository.get_for_owner(
        worker_instance_id=worker.id,
        owner_user_id='user-1',
    ) == heartbeated
    assert await repository.get_for_owner(
        worker_instance_id=worker.id,
        owner_user_id='user-other',
    ) is None
    assert await repository.list_for_owner(owner_user_id='user-1') == (heartbeated,)
    enabled_workers = await repository.list_enabled(project_id='project-a')
    readiness = await repository.readiness(
        project_id='project-a',
        active_since=timestamp,
        harness={'kind': 'codex_cli', 'version': 'v1', 'config': {}},
    )

    assert readiness.registered_worker_count == 1
    assert readiness.active_worker_count == 1
    assert readiness.compatible_worker_count == 0
    assert repeated_enablement == enabled_for_a
    assert enabled_workers == (
        WorkerInstanceProjectDocument(
            worker=heartbeated,
            enablement=enabled_for_a,
        ),
    )
    assert await repository.list_enabled_projects(
        worker_instance_id=worker.id,
    ) == (enabled_for_a, enabled_for_b)

    await repository.disable_project(
        worker_instance_id=worker.id,
        project_id='project-a',
    )

    assert await repository.list_enabled(project_id='project-a') == ()
    assert await repository.list_enabled_projects(
        worker_instance_id=worker.id,
    ) == (enabled_for_b,)
