"""Migration coverage for User-owned Activities."""

import sqlite3

from tests.integration.migrations.test_instruction_catalog_migration import (
    SQLITE_MIGRATIONS,
    apply_migrations,
    insert_workspace,
)


def test_activity_ownership_migration_uses_earliest_workspace_owner() -> None:
    """Legacy Activities move to the earliest owner and survive workspace deletion."""

    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    apply_migrations(connection, through='0052_logical_model_overrides')
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
            id, workspace_id, name, description, status, activity_type,
            config_json, created_at, created_by, updated_at, updated_by
        ) VALUES (
            'activity-1', 'workspace-1', 'Activity', 'Description', 'active',
            'approval', '{}', 'now', 'user-earlier', 'now', 'user-earlier'
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

    connection.executescript(
        (SQLITE_MIGRATIONS / '0053_user_owned_activities.sql').read_text(
            encoding='utf-8',
        ),
    )

    migrated = connection.execute(
        'SELECT user_id, workspace_id FROM activities WHERE id = ?',
        ('activity-1',),
    ).fetchone()

    assert migrated is not None
    assert migrated['user_id'] == 'user-earlier'
    assert migrated['workspace_id'] == 'workspace-1'
    assert connection.execute(
        '''
        SELECT activity_id
        FROM pipeline_steps
        WHERE workspace_id = 'workspace-1' AND pipeline_id = 'pipeline-1'
        ''',
    ).fetchone()['activity_id'] == 'activity-1'

    connection.execute('DELETE FROM workspaces WHERE id = ?', ('workspace-1',))
    surviving = connection.execute(
        'SELECT workspace_id FROM activities WHERE id = ?',
        ('activity-1',),
    ).fetchone()

    assert surviving is not None
    assert surviving['workspace_id'] is None
