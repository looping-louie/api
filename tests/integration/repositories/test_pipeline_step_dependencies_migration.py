"""Migration coverage for Pipeline step dependency edges."""

from __future__ import annotations

import asyncio
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


def apply_migrations_through_0026(connection: sqlite3.Connection) -> None:
    """Apply the schema state immediately before dependency edges."""

    for path in sorted(SQLITE_MIGRATIONS.glob('*.sql')):
        if path.stem == '0027_pipeline_step_dependencies':
            break
        connection.executescript(path.read_text(encoding='utf-8'))


def test_pipeline_step_dependencies_migration_preserves_existing_steps(
    tmp_path: Path,
) -> None:
    """The forward migration adds edges without changing existing steps."""

    database_path = tmp_path / 'pipeline-step-dependencies.db'
    connection = sqlite3.connect(database_path)
    apply_migrations_through_0026(connection)
    connection.execute(
        """
        INSERT INTO workspaces (id, name, created_at, updated_at)
        VALUES ('workspace-1', 'Workspace 1', '2026-08-13T10:00:00Z', '2026-08-13T10:00:00Z')
        """
    )
    connection.execute(
        """
        INSERT INTO activities (
            id, workspace_id, name, description, status, activity_type,
            config_json, created_at, created_by, updated_at, updated_by
        )
        VALUES
            ('activity-1', 'workspace-1', 'Prepare', '', 'active', 'approval',
             '{}', '2026-08-13T10:00:00Z', 'user-1', '2026-08-13T10:00:00Z', 'user-1'),
            ('activity-2', 'workspace-1', 'Validate', '', 'active', 'approval',
             '{}', '2026-08-13T10:00:00Z', 'user-1', '2026-08-13T10:00:00Z', 'user-1')
        """
    )
    connection.execute(
        """
        INSERT INTO pipelines (
            id, workspace_id, name, description, status, created_at,
            created_by, updated_at, updated_by
        )
        VALUES (
            'pipeline-1', 'workspace-1', 'Validation', '', 'active',
            '2026-08-13T10:00:00Z', 'user-1', '2026-08-13T10:00:00Z', 'user-1'
        )
        """
    )
    connection.execute(
        """
        INSERT INTO pipeline_steps (workspace_id, pipeline_id, position, activity_id)
        VALUES
            ('workspace-1', 'pipeline-1', 0, 'activity-1'),
            ('workspace-1', 'pipeline-1', 1, 'activity-2')
        """
    )
    connection.commit()
    connection.close()

    migrations_path = tmp_path / 'migrations'
    migrations_path.mkdir()
    migration_path = SQLITE_MIGRATIONS / '0027_pipeline_step_dependencies.sql'
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
    steps = connection.execute(
        """
        SELECT position, activity_id
        FROM pipeline_steps
        WHERE pipeline_id = ?
        ORDER BY position
        """,
        ('pipeline-1',),
    ).fetchall()
    connection.execute(
        """
        INSERT INTO pipeline_step_dependencies (
            workspace_id, pipeline_id, dependent_position,
            dependency_activity_id, condition
        )
        VALUES ('workspace-1', 'pipeline-1', 1, 'activity-1', 'succeed')
        """
    )
    dependencies = connection.execute(
        """
        SELECT dependent_position, dependency_activity_id, condition
        FROM pipeline_step_dependencies
        """
    ).fetchall()
    connection.close()

    assert steps == [(0, 'activity-1'), (1, 'activity-2')]
    assert dependencies == [(1, 'activity-1', 'succeed')]
