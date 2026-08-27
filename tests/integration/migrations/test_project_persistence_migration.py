"""Migration coverage for physical Project persistence names."""

from __future__ import annotations

import sqlite3

from tests.integration.migrations.test_instruction_catalog_migration import (
    SQLITE_MIGRATIONS,
    apply_migrations,
    insert_workspace,
)


def test_project_persistence_migration_preserves_project_placed_data() -> None:
    """Rename Workspace storage without losing Project-scoped data or keys."""

    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    apply_migrations(connection, through='0055_user_execution_defaults')
    insert_workspace(connection, 'project-1')
    connection.execute(
        '''
        INSERT INTO instructions (
            id, instruction_type, origin, owner_user_id, owner_workspace_id,
            name, name_key, content, metadata_json, enabled_by_default,
            deprecated, version, created_at, updated_at
        ) VALUES (
            'instruction-1', 'skill', 'custom', 'user-project-1', 'project-1',
            'Instruction', 'instruction', 'Content', '{}', 0, 0, 1, 'now', 'now'
        )
        ''',
    )
    connection.execute(
        '''
        INSERT INTO workspace_instruction_settings (
            workspace_id, instruction_id, enabled, created_at, updated_at
        ) VALUES ('project-1', 'instruction-1', 1, 'now', 'now')
        ''',
    )
    connection.execute(
        '''
        INSERT INTO activities (
            id, user_id, workspace_id, name, description, status, activity_type,
            config_json, created_at, created_by, updated_at, updated_by
        ) VALUES (
            'activity-1', 'user-project-1', 'project-1', 'Activity', 'Description',
            'active', 'approval', '{}', 'now', 'user-project-1', 'now', 'user-project-1'
        )
        ''',
    )
    connection.execute(
        '''
        INSERT INTO activity_runs (
            id, workspace_id, activity_id, input, status, state, next_action,
            iteration, token_revision, activity_snapshot_json, created_at,
            created_by, updated_at
        ) VALUES (
            'activity-run-1', 'project-1', 'activity-1', 'Input', 'in_progress',
            'awaiting_snapshot', 'collect_snapshot', 1, 0, '{}', 'now',
            'user-project-1', 'now'
        )
        ''',
    )
    connection.execute(
        '''
        INSERT INTO activity_run_checkpoints (
            workspace_id, run_id, token_revision, state, next_action, context_json, created_at
        ) VALUES (
            'project-1', 'activity-run-1', 0, 'awaiting_snapshot',
            'collect_snapshot', '{}', 'now'
        )
        ''',
    )
    connection.execute(
        '''
        INSERT INTO activity_run_idempotency (
            workspace_id, run_id, token_revision, idempotency_key, response_json, created_at
        ) VALUES ('project-1', 'activity-run-1', 0, 'request-1', '{}', 'now')
        ''',
    )
    connection.execute(
        '''
        INSERT INTO pipelines (
            id, user_id, name, description, status, created_at,
            created_by, updated_at, updated_by
        ) VALUES (
            'pipeline-1', 'user-project-1', 'Pipeline', 'Description', 'active',
            'now', 'user-project-1', 'now', 'user-project-1'
        )
        ''',
    )
    connection.execute(
        '''
        INSERT INTO pipeline_runs (
            id, workspace_id, pipeline_id, input, status, attempt,
            pipeline_snapshot_json, created_at, created_by, updated_at
        ) VALUES (
            'pipeline-run-1', 'project-1', 'pipeline-1', 'Input', 'prepared', 0,
            '{}', 'now', 'user-project-1', 'now'
        )
        ''',
    )
    connection.execute(
        '''
        INSERT INTO pipeline_run_steps (
            workspace_id, pipeline_run_id, position, activity_id, status,
            activity_snapshot_json, updated_at
        ) VALUES ('project-1', 'pipeline-run-1', 0, 'activity-1', 'pending', '{}', 'now')
        ''',
    )
    connection.execute(
        '''
        INSERT INTO pipeline_run_events (
            id, workspace_id, pipeline_run_id, event_type, actor_id, payload_json, created_at
        ) VALUES ('event-1', 'project-1', 'pipeline-run-1', 'created', 'user-project-1', '{}', 'now')
        ''',
    )
    connection.execute(
        '''
        INSERT INTO workers (
            id, workspace_id, registered_at, last_heartbeat_at, harnesses_json
        ) VALUES ('worker-1', 'project-1', 'now', 'now', '[]')
        ''',
    )

    connection.executescript(
        (SQLITE_MIGRATIONS / '0056_projects.sql').read_text(encoding='utf-8'),
    )

    table_names = {
        row['name']
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        )
    }
    project_columns = {
        (table_name, column_name)
        for table_name, column_name in connection.execute(
            """
            SELECT schema.name, columns.name
            FROM sqlite_master AS schema
            JOIN pragma_table_info(schema.name) AS columns
            WHERE schema.type = 'table'
              AND columns.name IN ('project_id', 'owner_project_id')
            """,
        )
    }
    foreign_key_errors = list(connection.execute('PRAGMA foreign_key_check'))

    assert {'projects', 'project_memberships', 'project_instruction_settings'} <= table_names
    assert 'workspaces' not in table_names
    assert 'workspace_memberships' not in table_names
    assert 'workspace_instruction_settings' not in table_names
    assert ('instructions', 'owner_project_id') in project_columns
    assert ('pipeline_runs', 'project_id') in project_columns
    assert ('workers', 'project_id') in project_columns
    assert foreign_key_errors == []
    assert connection.execute('SELECT project_id FROM project_memberships').fetchone()[0] == 'project-1'
    assert connection.execute('SELECT project_id FROM project_instruction_settings').fetchone()[0] == 'project-1'
    assert connection.execute('SELECT project_id FROM activity_run_checkpoints').fetchone()[0] == 'project-1'
    assert connection.execute('SELECT project_id FROM activity_run_idempotency').fetchone()[0] == 'project-1'
    assert connection.execute('SELECT project_id FROM pipeline_run_steps').fetchone()[0] == 'project-1'
    assert connection.execute('SELECT project_id FROM pipeline_run_events').fetchone()[0] == 'project-1'