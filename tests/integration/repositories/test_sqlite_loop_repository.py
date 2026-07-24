"""Integration tests for SQLite loop persistence."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import aiosqlite
import pytest

from src.app.models.loop import (
    LoopAgent,
    LoopChangelogEntry,
    LoopDocument,
    LoopOutputContract,
    LoopStopConditions,
)
from src.app.repositories.loops.sqlite_loop_repository import (
    SqliteLoopRepository,
)
from tests.integration.conftest import WorkspaceFactory


BASE_TIME = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)


def loop_document(
    *,
    loop_id: str = "loop-1",
    title: str = "Loop one",
    updated_at: datetime = BASE_TIME,
) -> LoopDocument:
    """Build one complete direct loop document."""

    return LoopDocument(
        id=loop_id,
        workspace_id="workspace-1",
        title=title,
        description="Produce an answer.",
        flow="direct",
        status="active",
        stop_conditions=LoopStopConditions(max_iterations=3),
        agents=(
            LoopAgent(
                id=f"{loop_id}-agent",
                model_id="model-1",
                persona_id="persona-1",
                role="generator",
            ),
        ),
        output_contract=LoopOutputContract(
            type="text",
            description="Answer.",
            files=(),
            schema=None,
        ),
        created_at=BASE_TIME,
        created_by="user-1",
        updated_at=updated_at,
        updated_by="user-1",
    )


def entry(
    document: LoopDocument,
    *,
    entry_id: str,
    change_type: str = "created",
    changed_at: datetime = BASE_TIME,
) -> LoopChangelogEntry:
    """Build a changelog entry for a repository mutation."""

    return LoopChangelogEntry(
        id=entry_id,
        loop_id=document.id,
        workspace_id=document.workspace_id,
        change_type=change_type,  # type: ignore[arg-type]
        actor_id="user-1",
        changed_at=changed_at,
        diff=None,
        content={"id": document.id},
    )


@pytest.mark.asyncio
async def test_create_get_list_and_paginate_loops(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """Repository round-trips aggregates and returns fixed caller pages."""

    await create_workspace(workspace_id="workspace-1")
    repository = SqliteLoopRepository(sqlite_database_path)
    for position in range(12):
        document = loop_document(
            loop_id=f"loop-{position:02d}",
            title=f"Loop {position:02d}",
            updated_at=BASE_TIME + timedelta(seconds=position),
        )
        await repository.create(
            document=document,
            changelog_entry=entry(
                document,
                entry_id=f"entry-{position:02d}",
                changed_at=document.updated_at,
            ),
        )

    first, total = await repository.list(
        workspace_id="workspace-1",
        offset=0,
        limit=10,
    )
    second, second_total = await repository.list(
        workspace_id="workspace-1",
        offset=10,
        limit=10,
    )
    stored = await repository.get(
        workspace_id="workspace-1",
        loop_id="loop-00",
    )

    assert total == second_total == 12
    assert len(first) == 10
    assert len(second) == 2
    assert stored == loop_document(loop_id="loop-00", title="Loop 00")


@pytest.mark.asyncio
async def test_update_rolls_back_when_changelog_insert_fails(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """A failed changelog insert leaves loop fields and agents unchanged."""

    await create_workspace(workspace_id="workspace-1")
    repository = SqliteLoopRepository(sqlite_database_path)
    original = loop_document()
    creation = entry(original, entry_id="duplicate-entry")
    await repository.create(
        document=original,
        changelog_entry=creation,
    )
    changed = replace(
        original,
        title="Changed title",
        agents=(
            LoopAgent(
                id="replacement-agent",
                model_id="model-2",
                persona_id="persona-2",
                role="reviewer",
            ),
        ),
        updated_at=BASE_TIME + timedelta(seconds=1),
    )

    with pytest.raises(aiosqlite.IntegrityError):
        await repository.update(
            document=changed,
            changelog_entry=entry(
                changed,
                entry_id="duplicate-entry",
                change_type="updated",
            ),
        )

    assert await repository.get(
        workspace_id="workspace-1",
        loop_id=original.id,
    ) == original


@pytest.mark.asyncio
async def test_delete_retains_newest_first_changelog(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """Deleting a loop retains all entries without a loop foreign key."""

    await create_workspace(workspace_id="workspace-1")
    repository = SqliteLoopRepository(sqlite_database_path)
    original = loop_document()
    await repository.create(
        document=original,
        changelog_entry=entry(original, entry_id="entry-1"),
    )
    updated = replace(
        original,
        description="Updated.",
        updated_at=BASE_TIME + timedelta(seconds=1),
    )
    await repository.update(
        document=updated,
        changelog_entry=entry(
            updated,
            entry_id="entry-2",
            change_type="updated",
            changed_at=updated.updated_at,
        ),
    )
    deleted = await repository.delete(
        workspace_id="workspace-1",
        loop_id=updated.id,
        changelog_entry=entry(
            updated,
            entry_id="entry-3",
            change_type="deleted",
            changed_at=BASE_TIME + timedelta(seconds=2),
        ),
    )
    entries, total = await repository.list_changelog(
        workspace_id="workspace-1",
        loop_id=updated.id,
        offset=0,
        limit=10,
    )

    assert deleted is True
    assert await repository.get(
        workspace_id="workspace-1",
        loop_id=updated.id,
    ) is None
    assert total == 3
    assert [item.change_type for item in entries] == [
        "deleted",
        "updated",
        "created",
    ]


@pytest.mark.asyncio
async def test_changelog_supports_offset_pages(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """Changelog pages retain the full total and newest-first order."""

    await create_workspace(workspace_id="workspace-1")
    repository = SqliteLoopRepository(sqlite_database_path)
    current = loop_document()
    await repository.create(
        document=current,
        changelog_entry=entry(current, entry_id="entry-00"),
    )
    for position in range(1, 12):
        current = replace(
            current,
            description=f"Update {position}",
            updated_at=BASE_TIME + timedelta(seconds=position),
        )
        await repository.update(
            document=current,
            changelog_entry=entry(
                current,
                entry_id=f"entry-{position:02d}",
                change_type="updated",
                changed_at=current.updated_at,
            ),
        )

    first, total = await repository.list_changelog(
        workspace_id="workspace-1",
        loop_id=current.id,
        offset=0,
        limit=10,
    )
    second, second_total = await repository.list_changelog(
        workspace_id="workspace-1",
        loop_id=current.id,
        offset=10,
        limit=10,
    )

    assert total == second_total == 12
    assert len(first) == 10
    assert [item.id for item in second] == ["entry-01", "entry-00"]
