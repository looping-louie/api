"""Integration coverage for one-time workspace loop installation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import aiosqlite
import pytest

from src.app.repositories.loops.sqlite_loop_repository import (
    SqliteLoopRepository,
)
from src.app.services.loops.catalog_seeder import seed_loop_catalog
from tests.integration.conftest import WorkspaceFactory


@pytest.mark.asyncio
async def test_catalog_loops_are_installed_once_and_remain_user_owned(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """Modified or deleted catalog loops must not be reset on later seeds."""

    await create_workspace(workspace_id="workspace-1")
    await create_workspace(workspace_id="workspace-2")
    identifiers = iter(f"id-{position}" for position in range(30))
    inserted = await seed_loop_catalog(
        database_path=sqlite_database_path,
        id_factory=lambda: next(identifiers),
        clock=lambda: datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
    )
    repository = SqliteLoopRepository(sqlite_database_path)
    workspace_one, total_one = await repository.list(
        workspace_id="workspace-1",
        offset=0,
        limit=10,
    )
    workspace_two, total_two = await repository.list(
        workspace_id="workspace-2",
        offset=0,
        limit=10,
    )

    assert inserted == 4
    assert total_one == total_two == 2
    assert {
        item.title
        for item in workspace_one
    } == {"shape ideas", "plan implementation"}
    assert {
        item.title
        for item in workspace_two
    } == {"shape ideas", "plan implementation"}

    shape = next(
        item
        for item in workspace_one
        if item.title == "shape ideas"
    )
    plan = next(
        item
        for item in workspace_one
        if item.title == "plan implementation"
    )
    async with aiosqlite.connect(sqlite_database_path) as connection:
        await connection.execute("PRAGMA foreign_keys = ON")
        await connection.execute(
            "UPDATE loops SET title = ? WHERE id = ?",
            ("custom shape", shape.id),
        )
        await connection.execute(
            "DELETE FROM loops WHERE id = ?",
            (plan.id,),
        )
        await connection.commit()

    repeated = await seed_loop_catalog(
        database_path=sqlite_database_path,
    )
    remaining, remaining_total = await repository.list(
        workspace_id="workspace-1",
        offset=0,
        limit=10,
    )

    assert repeated == 0
    assert remaining_total == 1
    assert remaining[0].title == "custom shape"
