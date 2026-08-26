"""Integration tests for SQLite activity-run persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import aiosqlite
import pytest

from src.app.models.activity_run import ActivityRunDocument
from src.app.repositories.activity_runs.errors import (
    ActivityRunInvalidTransitionError,
)
from src.app.repositories.activity_runs.sqlite_repository import (
    SqliteActivityRunRepository,
)


@pytest.mark.asyncio
async def test_activity_run_uses_dedicated_tables_and_replays_transition(
    sqlite_database_path: Path,
    create_workspace: object,
) -> None:
    """Activity runs persist with replay safety."""

    await create_workspace(workspace_id='workspace-1')
    timestamp = datetime(2026, 8, 14, tzinfo=UTC)
    async with aiosqlite.connect(sqlite_database_path) as connection:
        await connection.execute('PRAGMA foreign_keys = ON')
        await connection.execute(
            '''
            INSERT INTO users (id, created_at, updated_at)
            VALUES ('user-1', ?, ?)
            ''',
            (timestamp.isoformat(), timestamp.isoformat()),
        )
        await connection.execute(
            '''
            INSERT INTO activities (
                    id, user_id, workspace_id, name, description, status, activity_type,
                config_json, created_at, created_by, updated_at, updated_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                    'activity-1', 'user-1', 'workspace-1', 'Activity', '', 'active',
                'direct_loop', '{}', timestamp.isoformat(), 'user-1',
                timestamp.isoformat(), 'user-1',
            ),
        )
        await connection.commit()

    repository = SqliteActivityRunRepository(sqlite_database_path)
    document = ActivityRunDocument(
        id='run-1', workspace_id='workspace-1', activity_id='activity-1',
        input='Create a file.', status='in_progress', state='awaiting_snapshot',
        next_action='collect_snapshot', iteration=1, token_revision=0,
        continuation_token='token-0', activity_snapshot={'flow': 'direct'},
        execution_context={}, created_at=timestamp, created_by='user-1',
        updated_at=timestamp,
    )

    created = await repository.create(document=document)
    updated = await repository.transition(
        workspace_id='workspace-1', activity_id='activity-1', run_id='run-1',
        continuation_token='token-0', idempotency_key='request-1',
        expected_action='collect_snapshot', status='in_progress',
        state='awaiting_apply', next_action='apply_operations',
        next_continuation_token='token-1', execution_context={'operations': []},
        updated_at=timestamp,
    )
    replayed = await repository.transition(
        workspace_id='workspace-1', activity_id='activity-1', run_id='run-1',
        continuation_token='token-0', idempotency_key='request-1',
        expected_action='collect_snapshot', status='in_progress',
        state='awaiting_apply', next_action='apply_operations',
        next_continuation_token='token-1', execution_context={'operations': []},
        updated_at=timestamp,
    )

    async with aiosqlite.connect(sqlite_database_path) as connection:
        activity_count = await (await connection.execute(
            'SELECT COUNT(*) FROM activity_runs WHERE id = ?', ('run-1',)
        )).fetchone()

    assert created == document
    assert updated.state == 'awaiting_apply'
    assert replayed == updated
    assert activity_count == (1,)


@pytest.mark.asyncio
async def test_expired_pipeline_lease_cannot_advance_its_activity_child(
    sqlite_database_path: Path,
    create_workspace: object,
) -> None:
    """An expired worker cannot mutate the currently selected Pipeline child."""

    timestamp = datetime(2026, 8, 14, tzinfo=UTC)
    await create_workspace(workspace_id='workspace-1')
    await _insert_pipeline_child(
        database_path=sqlite_database_path,
        timestamp=timestamp,
        lease_expires_at=datetime(1970, 1, 1, tzinfo=UTC),
    )
    repository = SqliteActivityRunRepository(sqlite_database_path)

    assert not await repository.has_active_pipeline_lease(
        workspace_id='workspace-1',
        activity_run_id='run-1',
        pipeline_run_id='pipeline-run-1',
        lease_token='lease-1',
        now=timestamp,
    )

    with pytest.raises(ActivityRunInvalidTransitionError):
        await repository.transition(
            workspace_id='workspace-1', activity_id='activity-1', run_id='run-1',
            pipeline_run_id='pipeline-run-1', lease_token='lease-1',
            continuation_token='token-0', idempotency_key='request-1',
            expected_action='collect_snapshot', status='in_progress',
            state='awaiting_apply', next_action='apply_operations',
            next_continuation_token='token-1', execution_context={'operations': []},
            updated_at=timestamp,
        )


@pytest.mark.asyncio
async def test_waiting_human_pipeline_child_can_submit_a_decision_without_lease(
    sqlite_database_path: Path,
    create_workspace: object,
) -> None:
    """A human-owned child is authorized while its Pipeline waits lease-free."""

    timestamp = datetime(2026, 8, 14, tzinfo=UTC)
    await create_workspace(workspace_id='workspace-1')
    await _insert_pipeline_child(
        database_path=sqlite_database_path,
        timestamp=timestamp,
        lease_expires_at=timestamp,
    )
    async with aiosqlite.connect(sqlite_database_path) as connection:
        await connection.execute(
            '''
            UPDATE activity_runs
            SET state = 'awaiting_human_decision', next_action = 'submit_human_decision',
                activity_snapshot_json = '{"executor":"human"}'
            WHERE workspace_id = 'workspace-1' AND id = 'run-1'
            '''
        )
        await connection.execute(
            '''
            UPDATE pipeline_runs
            SET status = 'waiting', worker_id = NULL, lease_token = NULL,
                lease_expires_at = NULL
            WHERE workspace_id = 'workspace-1' AND id = 'pipeline-run-1'
            '''
        )
        await connection.commit()

    repository = SqliteActivityRunRepository(sqlite_database_path)
    updated = await repository.transition(
        workspace_id='workspace-1', activity_id='activity-1', run_id='run-1',
        pipeline_run_id='pipeline-run-1', continuation_token='token-0',
        idempotency_key='human-decision-1', expected_action='submit_human_decision',
        status='completed', state='completed', next_action='none',
        next_continuation_token=None,
        execution_context={'human_decision': {'decision': 'approved'}},
        updated_at=timestamp,
    )

    assert updated.status == 'completed'


async def _insert_pipeline_child(
    *,
    database_path: Path,
    timestamp: datetime,
    lease_expires_at: datetime,
) -> None:
    """Seed one claimed Pipeline run and its selected Activity child."""

    async with aiosqlite.connect(database_path) as connection:
        await connection.execute('PRAGMA foreign_keys = ON')
        await connection.execute(
            '''
            INSERT INTO users (id, created_at, updated_at)
            VALUES ('user-1', ?, ?)
            ''',
            (timestamp.isoformat(), timestamp.isoformat()),
        )
        await connection.execute(
            '''
            INSERT INTO activities (
                id, user_id, workspace_id, name, description, status, activity_type,
                config_json, created_at, created_by, updated_at, updated_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                'activity-1', 'user-1', 'workspace-1', 'Activity', '', 'active',
                'direct_loop', '{}', timestamp.isoformat(), 'user-1',
                timestamp.isoformat(), 'user-1',
            ),
        )
        await connection.execute(
            '''
            INSERT INTO activity_runs (
                id, workspace_id, activity_id, input, status, state, next_action,
                iteration, token_revision, continuation_token, activity_snapshot_json,
                execution_context_json, created_at, created_by, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                'run-1', 'workspace-1', 'activity-1', 'Create a file.',
                'in_progress', 'awaiting_snapshot', 'collect_snapshot', 1, 0,
                'token-0', '{"flow":"direct"}', '{}', timestamp.isoformat(),
                'user-1', timestamp.isoformat(),
            ),
        )
        await connection.execute(
            '''
            INSERT INTO activity_run_checkpoints (
                workspace_id, run_id, token_revision, continuation_token,
                state, next_action, context_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                'workspace-1', 'run-1', 0, 'token-0', 'awaiting_snapshot',
                'collect_snapshot', '{}', timestamp.isoformat(),
            ),
        )
        await connection.execute(
            '''
            INSERT INTO pipelines (
                id, workspace_id, name, description, status, created_at,
                created_by, updated_at, updated_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                'pipeline-1', 'workspace-1', 'Pipeline', '', 'active',
                timestamp.isoformat(), 'user-1', timestamp.isoformat(), 'user-1',
            ),
        )
        await connection.execute(
            '''
            INSERT INTO pipeline_runs (
                id, workspace_id, pipeline_id, input, status, worker_id, lease_token,
                lease_expires_at, attempt, current_activity_run_id,
                pipeline_snapshot_json, created_at, created_by, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                'pipeline-run-1', 'workspace-1', 'pipeline-1', 'Create a file.',
                'claimed', 'worker-1', 'lease-1', lease_expires_at.isoformat(), 1,
                'run-1', '{"steps":[]}', timestamp.isoformat(), 'user-1',
                timestamp.isoformat(),
            ),
        )
        await connection.execute(
            '''
            INSERT INTO pipeline_run_steps (
                workspace_id, pipeline_run_id, position, activity_id, status,
                activity_run_id, activity_snapshot_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                'workspace-1', 'pipeline-run-1', 0, 'activity-1', 'in_progress',
                'run-1', '{"flow":"direct"}', timestamp.isoformat(),
            ),
        )
        await connection.commit()
