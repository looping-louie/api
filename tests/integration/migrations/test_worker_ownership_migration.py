"""Migration coverage for Worker ownership backfill."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from tests.integration.migrations.test_instruction_catalog_migration import (
    SQLITE_MIGRATIONS,
    apply_migrations,
)


def test_worker_ownership_migration_uses_the_first_owner_of_earliest_enablement(
    tmp_path: Path,
) -> None:
    """Backfill ownership deterministically when legacy Workers span Projects."""

    database_path = tmp_path / 'worker-ownership.db'
    connection = sqlite3.connect(database_path)
    connection.execute('PRAGMA foreign_keys = ON')
    apply_migrations(connection, through='0060_worker_instances')
    connection.executemany(
        '''
        INSERT INTO users (id, created_at, updated_at)
        VALUES (?, 'now', 'now')
        ''',
        [('user-a',), ('user-b',), ('user-c',)],
    )
    connection.executemany(
        '''
        INSERT INTO projects (id, name, created_at, updated_at)
        VALUES (?, ?, 'now', 'now')
        ''',
        [('project-earliest', 'Earliest'), ('project-later', 'Later')],
    )
    connection.executemany(
        '''
        INSERT INTO project_memberships (
            project_id, user_id, role, is_default, created_at
        ) VALUES (?, ?, 'owner', 0, 'now')
        ''',
        [
            ('project-earliest', 'user-c'),
            ('project-earliest', 'user-a'),
            ('project-later', 'user-b'),
        ],
    )
    connection.execute(
        '''
        INSERT INTO worker_instances (
            id, registered_at, last_heartbeat_at, harnesses_json
        ) VALUES ('worker-1', 'now', 'now', '[]')
        ''',
    )
    connection.executemany(
        '''
        INSERT INTO worker_project_enablements (
            worker_instance_id, project_id, enabled_at
        ) VALUES ('worker-1', ?, ?)
        ''',
        [
            ('project-later', '2026-10-07T10:01:00+00:00'),
            ('project-earliest', '2026-10-07T10:00:00+00:00'),
        ],
    )
    connection.executescript(
        (SQLITE_MIGRATIONS / '0061_worker_ownership.sql').read_text(
            encoding='utf-8',
        ),
    )

    owner = connection.execute(
        "SELECT owner_user_id FROM worker_instances WHERE id = 'worker-1'",
    ).fetchone()
    connection.close()

    assert owner == ('user-a',)
