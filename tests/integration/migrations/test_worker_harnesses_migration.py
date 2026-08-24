"""Migration coverage for Worker Harness capability backfill."""

from __future__ import annotations

import sqlite3
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / 'migrations'
    / 'sqlite'
    / '0042_worker_harnesses.sql'
)


def test_worker_harness_migration_backfills_louie_for_existing_workers(
    tmp_path: Path,
) -> None:
    """Existing Worker registrations receive the immutable Louie capability."""

    database_path = tmp_path / 'worker-harnesses.db'
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE workers (
            id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            registered_at TEXT NOT NULL,
            last_heartbeat_at TEXT NOT NULL,
            PRIMARY KEY (workspace_id, id)
        )
        """
    )
    connection.execute(
        """
        INSERT INTO workers (
            id, workspace_id, registered_at, last_heartbeat_at
        ) VALUES (?, ?, ?, ?)
        """,
        (
            'worker-1',
            'workspace-1',
            '2026-08-24T00:00:00Z',
            '2026-08-24T00:00:00Z',
        ),
    )

    connection.executescript(MIGRATION_PATH.read_text(encoding='utf-8'))
    row = connection.execute(
        'SELECT harnesses_json FROM workers WHERE id = ?',
        ('worker-1',),
    ).fetchone()
    connection.close()

    assert row == ('[{"kind":"louie","version":"v1","config":{}}]',)
