"""Migration coverage for the local Project seed ID."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.app.repositories.infrastructure.local_tenant_seed import (
    ensure_local_tenant,
)
from tests.integration.migrations.test_instruction_catalog_migration import (
    SQLITE_MIGRATIONS,
    apply_migrations,
)


@pytest.mark.asyncio
async def test_local_project_seed_migration_preserves_default_membership(
    tmp_path: Path,
) -> None:
    """Upgrade the legacy local Project before startup reseeds it."""

    database_path = tmp_path / 'local-project.db'
    connection = sqlite3.connect(database_path)
    connection.execute('PRAGMA foreign_keys = ON')
    apply_migrations(connection, through='0056_projects')
    connection.execute(
        '''
        INSERT INTO users (id, created_at, updated_at)
        VALUES ('local-user', 'now', 'now')
        ''',
    )
    connection.execute(
        '''
        INSERT INTO projects (id, name, created_at, updated_at)
        VALUES ('local-workspace', 'Local workspace', 'now', 'now')
        ''',
    )
    connection.execute(
        '''
        INSERT INTO project_memberships (
            project_id, user_id, role, is_default, created_at
        ) VALUES ('local-workspace', 'local-user', 'owner', 1, 'now')
        ''',
    )
    connection.executescript(
        (SQLITE_MIGRATIONS / '0057_local_project_seed.sql').read_text(
            encoding='utf-8',
        ),
    )
    connection.close()

    await ensure_local_tenant(database_path=database_path)

    connection = sqlite3.connect(database_path)
    memberships = connection.execute(
        '''
        SELECT project_id, user_id, role, is_default
        FROM project_memberships
        ''',
    ).fetchall()
    connection.close()

    assert memberships == [('local-project', 'local-user', 'owner', 1)]


@pytest.mark.asyncio
async def test_local_project_seed_preserves_an_existing_default_project(
    tmp_path: Path,
) -> None:
    """Do not create a second default membership during local Project seeding."""

    database_path = tmp_path / 'existing-default-project.db'
    connection = sqlite3.connect(database_path)
    connection.execute('PRAGMA foreign_keys = ON')
    apply_migrations(connection)
    connection.execute(
        '''
        INSERT INTO users (id, created_at, updated_at)
        VALUES ('local-user', 'now', 'now')
        ''',
    )
    connection.execute(
        '''
        INSERT INTO projects (id, name, created_at, updated_at)
        VALUES ('existing-project', 'Existing project', 'now', 'now')
        ''',
    )
    connection.execute(
        '''
        INSERT INTO project_memberships (
            project_id, user_id, role, is_default, created_at
        ) VALUES ('existing-project', 'local-user', 'owner', 1, 'now')
        ''',
    )
    connection.commit()
    connection.close()

    await ensure_local_tenant(database_path=database_path)

    connection = sqlite3.connect(database_path)
    memberships = connection.execute(
        '''
        SELECT project_id, is_default
        FROM project_memberships
        ORDER BY project_id
        ''',
    ).fetchall()
    connection.close()

    assert memberships == [('existing-project', 1), ('local-project', 0)]