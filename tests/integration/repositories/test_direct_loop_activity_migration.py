"""Migration coverage for flattening direct loop activities."""

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


def apply_migrations_through_0020(connection: sqlite3.Connection) -> None:
    """Apply the database schema before direct loop flattening."""

    for path in sorted(SQLITE_MIGRATIONS.glob('*.sql')):
        if path.stem == '0021_flatten_direct_loop_activities':
            break
        connection.executescript(path.read_text(encoding='utf-8'))


def test_direct_loop_becomes_a_direct_loop_activity(tmp_path: Path) -> None:
    """Direct loops migrate without disrupting referenced activities."""

    database_path = tmp_path / 'direct-loop.db'
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    apply_migrations_through_0020(connection)
    connection.execute(
        """
        INSERT INTO workspaces (id, name, created_at, updated_at)
        VALUES ('workspace-1', 'Workspace 1', '2026-08-13T10:00:00Z', '2026-08-13T10:00:00Z')
        """
    )
    connection.executemany(
        """
        INSERT INTO activities (
            id, workspace_id, title, description, status, activity_type,
            config_json, created_at, created_by, updated_at, updated_by
        )
        VALUES (?, 'workspace-1', ?, 'Description.', 'active', ?, ?,
                '2026-08-13T10:00:00Z', 'user-1', '2026-08-13T10:00:00Z', 'user-1')
        """,
        [
            ('direct-activity', 'Direct', 'loop', '{"type":"loop","flow":"direct","stop_conditions":{"max_tokens":10},"agents":[],"output_contract":{"type":"text","description":"Result."}}'),
            ('refinement-activity', 'Refinement', 'loop', '{"type":"loop","flow":"refinement","stop_conditions":{"max_tokens":10},"agents":[],"output_contract":{"type":"text","description":"Result."}}'),
        ],
    )
    connection.execute(
        """
        INSERT INTO pipelines (
            id, workspace_id, title, description, status, created_at,
            created_by, updated_at, updated_by
        )
        VALUES (
            'pipeline-1', 'workspace-1', 'Pipeline', 'Description.', 'active',
            '2026-08-13T10:00:00Z', 'user-1', '2026-08-13T10:00:00Z', 'user-1'
        )
        """
    )
    connection.execute(
        """
        INSERT INTO pipeline_steps (workspace_id, pipeline_id, position, activity_id)
        VALUES ('workspace-1', 'pipeline-1', 0, 'direct-activity')
        """
    )
    connection.commit()
    connection.close()

    migrations_path = tmp_path / 'migrations'
    migrations_path.mkdir()
    (migrations_path / '0021_flatten_direct_loop_activities.sql').write_text(
        (SQLITE_MIGRATIONS / '0021_flatten_direct_loop_activities.sql').read_text(
            encoding='utf-8'
        ),
        encoding='utf-8',
    )
    asyncio.run(
        run_sqlite_migrations(
            database_path=database_path,
            migrations_path=migrations_path,
        )
    )
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row

    activities = connection.execute(
        'SELECT id, activity_type, config_json FROM activities ORDER BY id'
    ).fetchall()
    pipeline_step = connection.execute(
        'SELECT activity_id FROM pipeline_steps'
    ).fetchone()
    entry = connection.execute(
        """
        SELECT actor_id, diff_json
        FROM activity_changelog_entries
        WHERE activity_id = 'direct-activity'
        """
    ).fetchone()

    assert [
        (row['id'], row['activity_type'], json.loads(row['config_json']))
        for row in activities
    ] == [
        (
            'direct-activity',
            'direct_loop',
            {
                'type': 'direct_loop',
                'stop_conditions': {'max_tokens': 10},
                'agents': [],
                'output_contract': {
                    'type': 'text',
                    'description': 'Result.',
                },
            },
        ),
        (
            'refinement-activity',
            'loop',
            {
                'type': 'loop',
                'flow': 'refinement',
                'stop_conditions': {'max_tokens': 10},
                'agents': [],
                'output_contract': {
                    'type': 'text',
                    'description': 'Result.',
                },
            },
        ),
    ]
    assert pipeline_step['activity_id'] == 'direct-activity'
    assert entry['actor_id'] == 'system:migration:0021'
    assert json.loads(entry['diff_json'])['type'] == {
        'from': 'loop',
        'to': 'direct_loop',
    }
