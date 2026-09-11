"""Migration coverage for User execution defaults."""

import json
import sqlite3

from tests.integration.migrations.test_instruction_catalog_migration import (
    SQLITE_MIGRATIONS,
    apply_migrations,
    insert_workspace,
)


def test_execution_defaults_migration_uses_default_workspace_without_replacing_harness() -> None:
    """Default Workspace policy backfills models while explicit User Harness wins."""

    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    apply_migrations(connection, through='0054_user_owned_pipelines')
    insert_workspace(connection, 'workspace-default')
    insert_workspace(connection, 'workspace-other')
    connection.execute(
        '''
        INSERT INTO users (id, created_at, updated_at, settings_json)
        VALUES (?, 'now', 'now', ?)
        ''',
        (
            'user-1',
            json.dumps({
                'default_harness': {'kind': 'codex_cli', 'version': 'v1', 'config': {}},
                'default_model_availability': 'enabled',
                'configured_models': [],
            }),
        ),
    )
    connection.executemany(
        '''
        INSERT INTO workspace_memberships (
            workspace_id, user_id, role, is_default, created_at
        ) VALUES (?, 'user-1', 'owner', ?, ?)
        ''',
        (
            ('workspace-other', 0, '2025-01-01T10:00:00+00:00'),
            ('workspace-default', 1, '2026-01-01T10:00:00+00:00'),
        ),
    )
    connection.executemany(
        '''
        INSERT INTO workspace_execution_defaults (
            workspace_id, model_id, harness_json, updated_at
        ) VALUES (?, ?, ?, 'now')
        ''',
        (
            ('workspace-default', 'model-default', '{"kind":"louie","version":"v1","config":{}}'),
            ('workspace-other', 'model-other', '{"kind":"louie","version":"v1","config":{}}'),
        ),
    )

    connection.executescript(
        (SQLITE_MIGRATIONS / '0055_user_execution_defaults.sql').read_text(
            encoding='utf-8',
        ),
    )

    settings = json.loads(connection.execute(
        'SELECT settings_json FROM users WHERE id = ?',
        ('user-1',),
    ).fetchone()['settings_json'])

    assert settings['default_model_id'] == 'model-default'
    assert settings['default_harness'] == {
        'kind': 'codex_cli',
        'version': 'v1',
        'config': {},
    }
    assert connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'workspace_execution_defaults'"
    ).fetchone() is None
