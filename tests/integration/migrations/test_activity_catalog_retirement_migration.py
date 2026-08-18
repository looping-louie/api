"""Migration coverage for retiring installed builtin activities."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


SQLITE_MIGRATIONS = (
    Path(__file__).resolve().parents[3]
    / 'migrations'
    / 'sqlite'
)


def apply_migrations_through_0017(connection: sqlite3.Connection) -> None:
    """Apply the schema that existed before builtin activity retirement."""

    for path in sorted(SQLITE_MIGRATIONS.glob('*.sql')):
        if path.stem == '0018_archive_builtin_activities':
            break
        connection.executescript(path.read_text(encoding='utf-8'))


def insert_workspace(connection: sqlite3.Connection) -> None:
    """Create the workspace required by the activity records."""

    connection.execute(
        """
        INSERT INTO workspaces (id, name, created_at, updated_at)
        VALUES ('workspace-1', 'Workspace 1', '2026-08-12T10:00:00Z', '2026-08-12T10:00:00Z')
        """
    )


def insert_activity(
    connection: sqlite3.Connection,
    *,
    activity_id: str,
    title: str,
) -> None:
    """Create an active loop activity with a stable pre-migration timestamp."""

    connection.execute(
        """
        INSERT INTO activities (
            id, workspace_id, title, description, status, activity_type,
            config_json, created_at, created_by, updated_at, updated_by
        )
        VALUES (?, 'workspace-1', ?, 'Description.', 'active', 'loop', '{}',
                '2026-08-12T10:00:00Z', 'user-1', '2026-08-12T10:00:00Z', 'user-1')
        """,
        (activity_id, title),
    )


def test_installed_activities_are_archived_without_removing_history() -> None:
    """Retirement archives only installed records and retains dependent data."""

    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    apply_migrations_through_0017(connection)
    insert_workspace(connection)
    insert_activity(
        connection,
        activity_id='installed-activity',
        title='Retired builtin activity',
    )
    insert_activity(
        connection,
        activity_id='user-activity',
        title='User activity',
    )
    connection.execute(
        """
        INSERT INTO activity_catalog_installations (
            workspace_id, catalog_activity_id, activity_id, installed_at
        )
        VALUES ('workspace-1', 'builtin:loop:retired', 'installed-activity', '2026-08-12T10:00:00Z')
        """
    )
    connection.execute(
        """
        INSERT INTO loop_runs (
            id, workspace_id, loop_id, activity_id, input, status, state,
            next_action, iteration, token_revision, continuation_token,
            loop_snapshot_json, execution_context_json, created_at, created_by,
            updated_at
        )
        VALUES (
            'run-1', 'workspace-1', NULL, 'installed-activity', 'Run activity.',
            'in_progress', 'awaiting_snapshot', 'collect_snapshot', 1, 0, NULL,
            '{}', '{}', '2026-08-12T10:00:00Z', 'user-1', '2026-08-12T10:00:00Z'
        )
        """
    )
    connection.commit()

    migration = (
        SQLITE_MIGRATIONS / '0018_archive_builtin_activities.sql'
    ).read_text(encoding='utf-8')
    connection.executescript(migration)
    connection.executescript(migration)

    activities = connection.execute(
        'SELECT id, status, title FROM activities ORDER BY id'
    ).fetchall()
    installation = connection.execute(
        'SELECT activity_id FROM activity_catalog_installations'
    ).fetchone()
    run = connection.execute(
        'SELECT activity_id FROM loop_runs WHERE id = \'run-1\''
    ).fetchone()
    entries = connection.execute(
        """
        SELECT id, actor_id, diff_json, content_json
        FROM activity_changelog_entries
        WHERE activity_id = 'installed-activity'
        """
    ).fetchall()

    assert [tuple(row) for row in activities] == [
        ('installed-activity', 'archived', 'Retired builtin activity'),
        ('user-activity', 'active', 'User activity'),
    ]
    assert installation['activity_id'] == 'installed-activity'
    assert run['activity_id'] == 'installed-activity'
    assert len(entries) == 1
    assert entries[0]['id'] == (
        'migration:0018:archive:776F726B73706163652D31:696E7374616C6C65642D6163746976697479'
    )
    assert entries[0]['actor_id'] == 'system:migration:0018'
    assert json.loads(entries[0]['diff_json']) == {
        'status': {'from': 'active', 'to': 'archived'},
    }
    assert json.loads(entries[0]['content_json']) == {'status': 'archived'}
