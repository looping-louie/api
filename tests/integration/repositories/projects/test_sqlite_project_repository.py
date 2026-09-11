"""Integration tests for SQLite project persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import aiosqlite
import pytest

from src.app.models.project import ProjectDocument
from src.app.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.app.repositories.projects import SqliteProjectRepository


def project_document(project_id: str) -> ProjectDocument:
    """Build one deterministic Project persistence document."""

    timestamp = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    return ProjectDocument(
        id=project_id,
        name=f'Project {project_id}',
        created_at=timestamp,
        updated_at=timestamp,
    )


@pytest.mark.asyncio
async def test_create_assigns_the_first_project_as_owner_default(
    sqlite_database_path: Path,
) -> None:
    """Creation stores owner membership and keeps the first default Project."""

    repository = SqliteProjectRepository(SqliteDatabase(sqlite_database_path))
    first = project_document('project-1')
    second = project_document('project-2')

    await repository.create(project=first, owner_id='user-1')
    await repository.create(project=second, owner_id='user-1')

    assert await repository.list_for_user(user_id='user-1') == [first, second]

    async with aiosqlite.connect(sqlite_database_path) as connection:
        rows = await (
            await connection.execute(
                '''
                SELECT project_id, role, is_default
                FROM project_memberships
                WHERE user_id = ?
                ORDER BY project_id
                ''',
                ('user-1',),
            )
        ).fetchall()

    assert rows == [
        ('project-1', 'owner', 1),
        ('project-2', 'owner', 0),
    ]


@pytest.mark.asyncio
async def test_get_and_update_project_persist_its_metadata(
    sqlite_database_path: Path,
) -> None:
    """Project persistence returns and updates one stored document."""

    repository = SqliteProjectRepository(SqliteDatabase(sqlite_database_path))
    created = project_document('project-1')
    updated = ProjectDocument(
        id=created.id,
        name='Updated project',
        created_at=created.created_at,
        updated_at=datetime(2026, 8, 26, 11, 0, tzinfo=UTC),
    )
    await repository.create(project=created, owner_id='user-1')

    assert await repository.get_project(project_id=created.id) == created
    assert await repository.update_project(project=updated) == updated
    assert await repository.get_project(project_id=updated.id) == updated
