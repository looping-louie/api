"""Integration tests for SQLite workspace persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import aiosqlite
import pytest

from src.app.models.workspace import WorkspaceDocument
from src.app.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.app.repositories.workspaces import SqliteWorkspaceRepository


def workspace_document(workspace_id: str) -> WorkspaceDocument:
    """Build one deterministic workspace persistence document."""

    timestamp = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    return WorkspaceDocument(
        id=workspace_id,
        name=f'Workspace {workspace_id}',
        created_at=timestamp,
        updated_at=timestamp,
    )


@pytest.mark.asyncio
async def test_create_assigns_the_first_workspace_as_owner_default(
    sqlite_database_path: Path,
) -> None:
    """Creation stores owner membership and keeps the first default workspace."""

    repository = SqliteWorkspaceRepository(SqliteDatabase(sqlite_database_path))
    first = workspace_document('workspace-1')
    second = workspace_document('workspace-2')

    await repository.create(workspace=first, owner_id='user-1')
    await repository.create(workspace=second, owner_id='user-1')

    assert await repository.list_for_user(user_id='user-1') == [first, second]

    async with aiosqlite.connect(sqlite_database_path) as connection:
        rows = await (
            await connection.execute(
                '''
                SELECT workspace_id, role, is_default
                FROM workspace_memberships
                WHERE user_id = ?
                ORDER BY workspace_id
                ''',
                ('user-1',),
            )
        ).fetchall()

    assert rows == [
        ('workspace-1', 'owner', 1),
        ('workspace-2', 'owner', 0),
    ]