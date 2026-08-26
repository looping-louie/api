"""Migration coverage for User-owned Pipelines."""

import sqlite3

from tests.integration.migrations.test_instruction_catalog_migration import (
    SQLITE_MIGRATIONS,
    apply_migrations,
    insert_workspace,
)


def test_pipeline_ownership_migration_preserves_workspace_placed_runs() -> None:
    """Legacy Pipelines move to their earliest owner without moving their runs."""

    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    apply_migrations(connection, through='0053_user_owned_activities')
    insert_workspace(connection, 'workspace-1')
    connection.execute(
        '''
        INSERT INTO users (id, created_at, updated_at)
        VALUES ('user-earlier', '2025-01-01T10:00:00+00:00', '2025-01-01T10:00:00+00:00')
        ''',
    )
    connection.execute(
        '''
        INSERT INTO workspace_memberships (
            workspace_id, user_id, role, is_default, created_at
        ) VALUES ('workspace-1', 'user-earlier', 'owner', 0, '2025-01-01T10:00:00+00:00')
        ''',
    )
    connection.execute(
        '''
        INSERT INTO activities (
            id, user_id, workspace_id, name, description, status, activity_type,
            config_json, created_at, created_by, updated_at, updated_by
        ) VALUES (
            'activity-1', 'user-earlier', 'workspace-1', 'Activity', 'Description',
            'active', 'approval', '{}', 'now', 'user-earlier', 'now', 'user-earlier'
        )
        ''',
    )
    connection.execute(
        '''
        INSERT INTO pipelines (
            id, workspace_id, name, description, status, created_at,
            created_by, updated_at, updated_by
        ) VALUES (
            'pipeline-1', 'workspace-1', 'Pipeline', 'Description', 'active',
            'now', 'user-earlier', 'now', 'user-earlier'
        )
        ''',
    )
    connection.execute(
        '''
        INSERT INTO pipeline_steps (workspace_id, pipeline_id, position, activity_id)
        VALUES ('workspace-1', 'pipeline-1', 0, 'activity-1')
        ''',
    )
    connection.execute(
        '''
        INSERT INTO pipeline_runs (
            id, workspace_id, pipeline_id, input, commit_mode, status, worker_id,
            lease_token, lease_expires_at, attempt, current_activity_run_id,
            pipeline_snapshot_json, created_at, created_by, updated_at
        ) VALUES (
            'run-1', 'workspace-1', 'pipeline-1', 'Input', 'allow', 'prepared',
            NULL, NULL, NULL, 0, NULL, '{}', 'now', 'user-earlier', 'now'
        )
        ''',
    )

    connection.executescript(
        (SQLITE_MIGRATIONS / '0054_user_owned_pipelines.sql').read_text(
            encoding='utf-8',
        ),
    )

    pipeline = connection.execute(
        'SELECT user_id FROM pipelines WHERE id = ?',
        ('pipeline-1',),
    ).fetchone()
    step = connection.execute(
        'SELECT activity_id FROM pipeline_steps WHERE pipeline_id = ?',
        ('pipeline-1',),
    ).fetchone()
    run = connection.execute(
        'SELECT workspace_id, pipeline_id FROM pipeline_runs WHERE id = ?',
        ('run-1',),
    ).fetchone()

    assert pipeline is not None
    assert pipeline['user_id'] == 'user-earlier'
    assert step is not None
    assert step['activity_id'] == 'activity-1'
    assert run is not None
    assert run['workspace_id'] == 'workspace-1'
    assert run['pipeline_id'] == 'pipeline-1'