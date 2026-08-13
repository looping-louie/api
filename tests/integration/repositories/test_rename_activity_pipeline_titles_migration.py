"""Migration coverage for Activity and Pipeline title-to-name renames."""

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


def apply_migrations_through_0024(connection: sqlite3.Connection) -> None:
    """Apply the schema state immediately before the name migration."""

    for path in sorted(SQLITE_MIGRATIONS.glob('*.sql')):
        if path.stem == '0025_rename_activity_pipeline_titles':
            break
        connection.executescript(path.read_text(encoding='utf-8'))


def test_activity_and_pipeline_titles_are_renamed_in_records_and_history(
    tmp_path: Path,
) -> None:
    """The forward migration preserves persisted values and history keys."""

    database_path = tmp_path / 'rename-activity-pipeline-titles.db'
    connection = sqlite3.connect(database_path)
    apply_migrations_through_0024(connection)
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
            'activity-1', 'workspace-1', 'Activity title', 'Description.',
            'active', 'approval', '{}', '2026-08-13T10:00:00Z', 'user-1',
            '2026-08-13T10:00:00Z', 'user-1'
        )
        """
    )
    connection.execute(
        """
        INSERT INTO pipelines (
            id, workspace_id, title, description, status, created_at,
            created_by, updated_at, updated_by
        )
        VALUES (
            'pipeline-1', 'workspace-1', 'Pipeline title', 'Description.',
            'active', '2026-08-13T10:00:00Z', 'user-1',
            '2026-08-13T10:00:00Z', 'user-1'
        )
        """
    )
    connection.execute(
        """
        INSERT INTO pipeline_steps (workspace_id, pipeline_id, position, activity_id)
        VALUES ('workspace-1', 'pipeline-1', 0, 'activity-1')
        """
    )
    for table, identifier in (
        ('activity_changelog_entries', 'activity-1'),
        ('pipeline_changelog_entries', 'pipeline-1'),
    ):
        id_field = 'activity_id' if table.startswith('activity') else 'pipeline_id'
        connection.execute(
            f"""
            INSERT INTO {table} (
                id, {id_field}, workspace_id, change_type, actor_id, changed_at,
                diff_json, content_json
            )
            VALUES (?, ?, 'workspace-1', 'updated', 'user-1',
                    '2026-08-13T10:00:00Z', ?, ?)
            """,
            (
                f'{table}-entry',
                identifier,
                json.dumps({'title': {'from': 'Before', 'to': 'After'}}),
                json.dumps({'title': f'{identifier} title'}),
            ),
        )
    connection.commit()
    connection.close()

    migrations_path = tmp_path / 'migrations'
    migrations_path.mkdir()
    migration_path = SQLITE_MIGRATIONS / '0025_rename_activity_pipeline_titles.sql'
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
    activity = connection.execute('SELECT name FROM activities').fetchone()
    pipeline = connection.execute('SELECT name FROM pipelines').fetchone()
    activity_columns = connection.execute('PRAGMA table_info(activities)').fetchall()
    pipeline_columns = connection.execute('PRAGMA table_info(pipelines)').fetchall()
    activity_history = connection.execute(
        'SELECT diff_json, content_json FROM activity_changelog_entries'
    ).fetchone()
    pipeline_history = connection.execute(
        'SELECT diff_json, content_json FROM pipeline_changelog_entries'
    ).fetchone()
    pipeline_step = connection.execute(
        'SELECT activity_id FROM pipeline_steps WHERE pipeline_id = ?',
        ('pipeline-1',),
    ).fetchone()
    connection.close()

    assert activity == ('Activity title',)
    assert pipeline == ('Pipeline title',)
    assert 'name' in [column[1] for column in activity_columns]
    assert 'title' not in [column[1] for column in activity_columns]
    assert 'name' in [column[1] for column in pipeline_columns]
    assert 'title' not in [column[1] for column in pipeline_columns]
    assert json.loads(activity_history[0]) == {
        'name': {'from': 'Before', 'to': 'After'},
    }
    assert json.loads(activity_history[1]) == {'name': 'activity-1 title'}
    assert json.loads(pipeline_history[0]) == {
        'name': {'from': 'Before', 'to': 'After'},
    }
    assert json.loads(pipeline_history[1]) == {'name': 'pipeline-1 title'}
    assert pipeline_step == ('activity-1',)
