"""Integration tests for SQLite activity-run persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import aiosqlite
import pytest

from src.app.models.activity_run import ActivityRunDocument
from src.app.repositories.activity_runs.sqlite_repository import (
    SqliteActivityRunRepository,
)


@pytest.mark.asyncio
async def test_activity_run_uses_dedicated_tables_and_replays_transition(
    sqlite_database_path: Path,
    create_workspace: object,
) -> None:
    """Activity runs persist separately from legacy loop runs with replay safety."""

    await create_workspace(workspace_id='workspace-1')
    timestamp = datetime(2026, 8, 14, tzinfo=UTC)
    async with aiosqlite.connect(sqlite_database_path) as connection:
        await connection.execute('PRAGMA foreign_keys = ON')
        await connection.execute(
            '''
            INSERT INTO activities (
                id, workspace_id, name, description, status, activity_type,
                config_json, created_at, created_by, updated_at, updated_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                'activity-1', 'workspace-1', 'Activity', '', 'active',
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
        loop_count = await (await connection.execute(
            'SELECT COUNT(*) FROM loop_runs WHERE id = ?', ('run-1',)
        )).fetchone()

    assert created == document
    assert updated.state == 'awaiting_apply'
    assert replayed == updated
    assert activity_count == (1,)
    assert loop_count == (0,)
