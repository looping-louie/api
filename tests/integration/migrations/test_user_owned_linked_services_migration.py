"""Migration coverage for user-owned linked services."""

import sqlite3

import pytest

from tests.integration.migrations.test_instruction_catalog_migration import (
    SQLITE_MIGRATIONS,
    apply_migrations,
    insert_workspace,
)


def test_user_ownership_migration_uses_earliest_workspace_owner() -> None:
    """Legacy services move to the earliest owner and survive workspace deletion."""

    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    apply_migrations(connection, through='0049_user_persona_settings')
    insert_workspace(connection, 'workspace-1')
    connection.execute(
        '''
        INSERT INTO users (id, created_at, updated_at)
        VALUES ('user-earlier', '2026-07-22T10:00:00+00:00', '2026-07-22T10:00:00+00:00')
        ''',
    )
    connection.execute(
        '''
        INSERT INTO workspace_memberships (
            workspace_id, user_id, role, is_default, created_at
        ) VALUES ('workspace-1', 'user-earlier', 'owner', 0, '2026-07-22T10:00:00+00:00')
        ''',
    )
    connection.execute(
        '''
        INSERT INTO linked_services (
            id, workspace_id, name, provider_type, created_at, updated_at
        ) VALUES ('service-1', 'workspace-1', 'primary', 'openai', 'now', 'now')
        ''',
    )

    connection.executescript(
        (SQLITE_MIGRATIONS / '0050_user_owned_linked_services.sql').read_text(
            encoding='utf-8',
        ),
    )

    migrated = connection.execute(
        'SELECT user_id FROM linked_services WHERE id = ?',
        ('service-1',),
    ).fetchone()
    columns = [
        row['name']
        for row in connection.execute('PRAGMA table_info(linked_services)')
    ]

    assert migrated is not None
    assert migrated['user_id'] == 'user-earlier'
    assert 'workspace_id' not in columns

    connection.execute('DELETE FROM workspaces WHERE id = ?', ('workspace-1',))
    assert connection.execute(
        'SELECT id FROM linked_services WHERE id = ?',
        ('service-1',),
    ).fetchone() is not None

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute('DELETE FROM users WHERE id = ?', ('user-earlier',))
