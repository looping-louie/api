"""Migration coverage for removing redundant Activity config types."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

from src.app.repositories.infrastructure.migration_runner import (
    run_sqlite_migrations,
)


SQLITE_MIGRATIONS = (
    Path(__file__).resolve().parents[3]
    / 'migrations'
    / 'sqlite'
)


def apply_migrations_through_0023(connection: sqlite3.Connection) -> None:
    """Apply the schema state immediately before config type removal."""

    for path in sorted(SQLITE_MIGRATIONS.glob('*.sql')):
        if path.stem == '0024_remove_activity_config_type':
            break
        connection.executescript(path.read_text(encoding='utf-8'))


def test_activity_config_type_is_removed_from_records_and_history(
    tmp_path: Path,
) -> None:
    """The migration removes legacy config types without altering other data."""

    database_path = tmp_path / 'remove-activity-config-type.db'
    connection = sqlite3.connect(database_path)
    apply_migrations_through_0023(connection)
    connection.execute(
        """
        INSERT INTO workspaces (id, name, created_at, updated_at)
        VALUES ('workspace-1', 'Workspace 1', '2026-08-13T10:00:00Z', '2026-08-13T10:00:00Z')
        """
    )
    connection.execute(
        """
        INSERT INTO activities (
            id, workspace_id, title, description, status, activity_type,
            config_json, created_at, created_by, updated_at, updated_by
        )
        VALUES (
            'activity-1', 'workspace-1', 'Activity', 'Description.', 'active',
            'direct_loop', ?, '2026-08-13T10:00:00Z', 'user-1',
            '2026-08-13T10:00:00Z', 'user-1'
        )
        """,
        (
            json.dumps({
                'type': 'direct_loop',
                'stop_conditions': {'max_tokens': 10},
            }),
        ),
    )
    connection.execute(
        """
        INSERT INTO activity_changelog_entries (
            id, activity_id, workspace_id, change_type, actor_id, changed_at,
            diff_json, content_json
        )
        VALUES (
            'entry-1', 'activity-1', 'workspace-1', 'updated', 'user-1',
            '2026-08-13T10:00:00Z', ?, ?
        )
        """,
        (
            json.dumps({
                'config': {
                    'type': 'direct_loop',
                    'from': {'type': 'direct_loop'},
                    'to': {'type': 'direct_loop'},
                },
            }),
            json.dumps({
                'type': 'direct_loop',
                'config': {'type': 'direct_loop'},
            }),
        ),
    )
    connection.commit()
    connection.close()

    migrations_path = tmp_path / 'migrations'
    migrations_path.mkdir()
    migration_path = SQLITE_MIGRATIONS / '0024_remove_activity_config_type.sql'
    (migrations_path / migration_path.name).write_text(
        migration_path.read_text(encoding='utf-8'),
        encoding='utf-8',
    )
    asyncio.run(
        run_sqlite_migrations(
            database_path=database_path,
            migrations_path=migrations_path,
        )
    )
    connection = sqlite3.connect(database_path)
    activity = connection.execute(
        'SELECT config_json FROM activities WHERE id = ?',
        ('activity-1',),
    ).fetchone()
    entry = connection.execute(
        """
        SELECT diff_json, content_json
        FROM activity_changelog_entries
        WHERE id = ?
        """,
        ('entry-1',),
    ).fetchone()

    assert json.loads(activity[0]) == {
        'stop_conditions': {'max_tokens': 10},
    }
    assert json.loads(entry[0]) == {
        'config': {'from': {}, 'to': {}},
    }
    assert json.loads(entry[1]) == {
        'type': 'direct_loop',
        'config': {},
    }
