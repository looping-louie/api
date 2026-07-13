"""Integration tests for SqliteCompositionRepository."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import aiosqlite
import pytest

from src.app.repositories.composition_repository import (
    SqliteCompositionRepository,
)
from tests.integration.factories import build_composition


WorkspaceFactory = Callable[..., Awaitable[None]]


@pytest.mark.asyncio
async def test_create_get_and_list_composition(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    repository = SqliteCompositionRepository(
        sqlite_database_path,
    )
    document = build_composition(
        items=(
            {
                "role": "reviewer",
                "persona_id": "persona-1",
                "skill_ids": [
                    "skill-1",
                ],
            },
        ),
    )

    created = await repository.create(
        document,
    )
    stored = await repository.get(
        workspace_id="workspace-1",
        composition_type="council",
        composition_id="composition-1",
    )
    summaries = await repository.list_summaries(
        workspace_id="workspace-1",
        composition_type="council",
    )

    assert created == document
    assert stored == document
    assert len(summaries) == 1
    assert summaries[0].id == document.id
    assert summaries[0].name == document.name
    assert summaries[0].version == 1


@pytest.mark.asyncio
async def test_update_replaces_items_with_optimistic_concurrency(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    repository = SqliteCompositionRepository(
        sqlite_database_path,
    )
    original = build_composition(
        items=(
            {
                "role": "reviewer",
                "persona_id": "persona-1",
                "skill_ids": [
                    "skill-1",
                ],
            },
        ),
    )

    await repository.create(
        original,
    )

    updated = replace(
        original,
        name="Updated Security Council",
        items=(
            {
                "role": "reviewer",
                "persona_id": "persona-2",
                "skill_ids": [
                    "skill-2",
                ],
            },
        ),
        version=2,
        updated_at=original.updated_at + timedelta(minutes=5),
    )

    stored = await repository.update(
        updated,
        expected_version=1,
    )

    assert stored == updated

    stale = replace(
        updated,
        version=3,
        updated_at=updated.updated_at + timedelta(minutes=5),
    )

    stale_result = await repository.update(
        stale,
        expected_version=1,
    )

    assert stale_result is None

    current = await repository.get(
        workspace_id="workspace-1",
        composition_type="council",
        composition_id="composition-1",
    )

    assert current == updated


@pytest.mark.asyncio
async def test_repository_isolates_workspace_and_type(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    await create_workspace(
        workspace_id="workspace-2",
    )
    repository = SqliteCompositionRepository(
        sqlite_database_path,
    )

    await repository.create(
        build_composition(
            composition_id="council-1",
            workspace_id="workspace-1",
            composition_type="council",
        )
    )
    await repository.create(
        build_composition(
            composition_id="loop-1",
            workspace_id="workspace-1",
            composition_type="loop",
            attributes={
                "council_id": "council-1",
                "max_iterations": 3,
            },
        )
    )
    await repository.create(
        build_composition(
            composition_id="council-2",
            workspace_id="workspace-2",
            composition_type="council",
        )
    )

    councils = await repository.list_summaries(
        workspace_id="workspace-1",
        composition_type="council",
    )
    loops = await repository.list_summaries(
        workspace_id="workspace-1",
        composition_type="loop",
    )

    assert [
        summary.id
        for summary in councils
    ] == [
        "council-1",
    ]
    assert [
        summary.id
        for summary in loops
    ] == [
        "loop-1",
    ]


@pytest.mark.asyncio
async def test_delete_cascades_items_and_dependencies(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    repository = SqliteCompositionRepository(
        sqlite_database_path,
    )

    await repository.create(
        build_composition(
            items=(
                {
                    "role": "reviewer",
                    "persona_id": "persona-1",
                    "skill_ids": [
                        "skill-1",
                    ],
                },
            ),
        )
    )

    deleted = await repository.delete(
        workspace_id="workspace-1",
        composition_type="council",
        composition_id="composition-1",
    )

    assert deleted is True

    async with aiosqlite.connect(
        sqlite_database_path,
    ) as connection:
        item_cursor = await connection.execute(
            """
            SELECT COUNT(*)
            FROM composition_items
            WHERE composition_id = ?
            """,
            ("composition-1",),
        )
        dependency_cursor = await connection.execute(
            """
            SELECT COUNT(*)
            FROM resource_dependencies
            WHERE source_id = ?
            """,
            ("composition-1",),
        )

        item_count = await item_cursor.fetchone()
        dependency_count = await dependency_cursor.fetchone()

    assert item_count is not None
    assert dependency_count is not None
    assert item_count[0] == 0
    assert dependency_count[0] == 0
