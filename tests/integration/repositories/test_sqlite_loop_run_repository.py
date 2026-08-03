"""Integration tests for SQLite loop-run persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite
import pytest

from src.app.models.loop_run import LoopRunDocument
from src.app.repositories.loop_runs.errors import LoopRunTokenConflictError
from src.app.repositories.loop_runs.sqlite_loop_run_repository import (
    SqliteLoopRunRepository,
)


@pytest.mark.asyncio
async def test_loop_run_persists_snapshot_and_parent_scope(
    sqlite_database_path: Path,
    create_workspace: object,
) -> None:
    """A loop run round-trips only through the loop that created it."""

    await create_workspace(workspace_id='workspace-1')
    timestamp = '2026-08-03T12:00:00+00:00'
    async with aiosqlite.connect(sqlite_database_path) as connection:
        await connection.execute('PRAGMA foreign_keys = ON')
        await connection.execute(
            '''
            INSERT INTO loops (
                id, workspace_id, title, description, flow, status,
                stop_conditions_json, output_contract_json, created_at,
                created_by, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                'loop-1',
                'workspace-1',
                'Loop',
                '',
                'direct',
                'active',
                json.dumps({'max_iterations': 1}),
                json.dumps(
                    {
                        'type': 'text',
                        'description': 'Output',
                        'files': [],
                        'schema': None,
                    }
                ),
                timestamp,
                'user-1',
                timestamp,
                'user-1',
            ),
        )
        await connection.commit()

    document = LoopRunDocument(
        id='run-1',
        workspace_id='workspace-1',
        loop_id='loop-1',
        input='Improve validation errors.',
        status='in_progress',
        state='awaiting_snapshot',
        next_action='collect_snapshot',
        iteration=1,
        token_revision=0,
        continuation_token='token-0',
        loop_snapshot={'id': 'loop-1', 'flow': 'direct'},
        execution_context={},
        created_at=datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
        created_by='user-1',
        updated_at=datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
    )
    repository = SqliteLoopRunRepository(sqlite_database_path)

    created = await repository.create(document=document)
    stored = await repository.get(
        workspace_id='workspace-1',
        loop_id='loop-1',
        run_id='run-1',
    )
    listed, total = await repository.list(
        workspace_id='workspace-1',
        loop_id='loop-1',
        offset=0,
        limit=10,
    )
    wrong_parent = await repository.get(
        workspace_id='workspace-1',
        loop_id='other-loop',
        run_id='run-1',
    )

    context = {
        'repo_context': 'Repository context.',
        'workspace_metadata': {
            'workspace_path': '/workspace/project',
            'source_commit_sha': 'abc123',
        },
        'constitution': 'Keep changes small.',
        'project_profile': {'source_file_count': 1},
    }
    continued = await repository.continue_collect_snapshot(
        workspace_id='workspace-1',
        loop_id='loop-1',
        run_id='run-1',
        continuation_token='token-0',
        idempotency_key='snapshot-1',
        execution_context=context,
        updated_at=datetime(2026, 8, 3, 12, 1, tzinfo=UTC),
    )
    replayed = await repository.continue_collect_snapshot(
        workspace_id='workspace-1',
        loop_id='loop-1',
        run_id='run-1',
        continuation_token='token-0',
        idempotency_key='snapshot-1',
        execution_context=context,
        updated_at=datetime(2026, 8, 3, 12, 2, tzinfo=UTC),
    )

    assert created == document
    assert stored == document
    assert listed == [document]
    assert total == 1
    assert wrong_parent is None
    assert continued.state == 'awaiting_generation'
    assert continued.execution_context == context
    assert continued.token_revision == 1
    assert continued.continuation_token is None
    assert replayed == continued

    with pytest.raises(LoopRunTokenConflictError):
        await repository.continue_collect_snapshot(
            workspace_id='workspace-1',
            loop_id='loop-1',
            run_id='run-1',
            continuation_token='token-0',
            idempotency_key='snapshot-2',
            execution_context=context,
            updated_at=datetime(2026, 8, 3, 12, 3, tzinfo=UTC),
        )