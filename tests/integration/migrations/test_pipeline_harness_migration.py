"""Migration coverage for Pipeline Harness backfill."""

from __future__ import annotations

import sqlite3
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / 'migrations'
    / 'sqlite'
    / '0041_pipeline_harness.sql'
)


def test_pipeline_harness_migration_backfills_louie_for_existing_pipelines(
    tmp_path: Path,
) -> None:
    """Existing Pipeline definitions receive the immutable Louie default."""

    database_path = tmp_path / 'pipeline-harness.db'
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE pipelines (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO pipelines (
            id, workspace_id, name, description, status, created_at,
            created_by, updated_at, updated_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            'pipeline-1',
            'workspace-1',
            'Pipeline',
            'Run work.',
            'active',
            '2026-08-24T00:00:00Z',
            'user-1',
            '2026-08-24T00:00:00Z',
            'user-1',
        ),
    )

    connection.executescript(MIGRATION_PATH.read_text(encoding='utf-8'))
    row = connection.execute(
        'SELECT harness_json FROM pipelines WHERE id = ?',
        ('pipeline-1',),
    ).fetchone()
    connection.close()

    assert row == ('{"kind":"louie","version":"v1","config":{}}',)
