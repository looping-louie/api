"""Shared fixtures for SQLite integration tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from pathlib import Path

import aiosqlite
import pytest
import pytest_asyncio

from src.app.repositories.infrastructure.migration_runner import (
    run_sqlite_migrations,
)
from src.app.repositories.infrastructure.sqlite_database import (
    SqliteDatabase,
)


WorkspaceMembershipSeed = tuple[str, str, bool]
WorkspaceFactory = Callable[..., Awaitable[None]]


@pytest_asyncio.fixture
async def sqlite_database_path(
    tmp_path: Path,
) -> AsyncIterator[Path]:
    """Create a migrated temporary SQLite database."""

    database_path = tmp_path / "looping-louie-test.db"

    await run_sqlite_migrations(
        database_path=database_path,
    )

    yield database_path


@pytest.fixture
def sqlite_database(
    sqlite_database_path: Path,
) -> SqliteDatabase:
    """Return the shared SQLite abstraction for the temporary database."""

    return SqliteDatabase(
        sqlite_database_path,
    )


@pytest.fixture
def create_workspace(
    sqlite_database_path: Path,
) -> WorkspaceFactory:
    """Return a helper that inserts workspaces and memberships."""

    async def create(
        *,
        workspace_id: str,
        name: str | None = None,
        memberships: Sequence[WorkspaceMembershipSeed] = (),
    ) -> None:
        timestamp = "2026-07-13T10:00:00+00:00"

        async with aiosqlite.connect(
            sqlite_database_path,
        ) as connection:
            await connection.execute(
                "PRAGMA foreign_keys = ON"
            )
            await connection.execute(
                """
                INSERT INTO workspaces (
                    id,
                    name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    workspace_id,
                    name or workspace_id,
                    timestamp,
                    timestamp,
                ),
            )

            if memberships:
                await connection.executemany(
                    """
                    INSERT INTO workspace_memberships (
                        workspace_id,
                        user_id,
                        role,
                        is_default,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            workspace_id,
                            user_id,
                            role,
                            int(is_default),
                            timestamp,
                        )
                        for user_id, role, is_default in memberships
                    ],
                )

            await connection.commit()

    return create
