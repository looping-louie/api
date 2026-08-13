"""Integration tests for SQLite pipeline persistence."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from src.app.models.activity import (
    ActivityChangelogEntry,
    ActivityDocument,
)
from src.app.models.pipeline import (
    PipelineActivityStep,
    PipelineChangelogEntry,
    PipelineDocument,
)
from src.app.repositories.activities.sqlite_repository import (
    SqliteActivityRepository,
)
from src.app.repositories.pipelines.sqlite_repository import (
    SqlitePipelineRepository,
)
from tests.factories.pipelines import (
    BASE_TIME,
    build_pipeline,
)
from tests.integration.conftest import WorkspaceFactory


def entry(
    document: PipelineDocument,
    *,
    entry_id: str,
    change_type: str = "created",
) -> PipelineChangelogEntry:
    """Build one pipeline changelog entry."""

    return PipelineChangelogEntry(
        id=entry_id,
        pipeline_id=document.id,
        workspace_id=document.workspace_id,
        change_type=change_type,  # type: ignore[arg-type]
        actor_id="user-1",
        changed_at=document.updated_at,
        diff=None,
        content={"id": document.id},
    )


async def seed_activities(
    database_path: Path,
    activity_ids: tuple[str, ...] = ('activity-1', 'activity-2', 'activity-3'),
) -> None:
    """Insert active activities referenced by repository fixtures."""

    repository = SqliteActivityRepository(database_path)
    for activity_id in activity_ids:
        document = ActivityDocument(
            id=activity_id,
            workspace_id='workspace-1',
            title=f'Activity {activity_id}',
            description='Complete one stage.',
            status='active',
            type='direct_loop',
            config={'type': 'direct_loop'},
            created_at=BASE_TIME,
            created_by='user-1',
            updated_at=BASE_TIME,
            updated_by='user-1',
        )
        await repository.create(
            document=document,
            changelog_entry=ActivityChangelogEntry(
                id=f'{activity_id}-entry',
                activity_id=activity_id,
                workspace_id='workspace-1',
                change_type='created',
                actor_id='user-1',
                changed_at=BASE_TIME,
                diff=None,
                content={'id': activity_id},
            ),
        )


@pytest.mark.asyncio
async def test_round_trips_ordered_activity_steps(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """Persistence retains exact activity order and duplicates."""

    await create_workspace(workspace_id="workspace-1")
    await seed_activities(sqlite_database_path)
    repository = SqlitePipelineRepository(sqlite_database_path)
    document = replace(
        build_pipeline(),
        steps=(
            PipelineActivityStep(activity_id='activity-1'),
            PipelineActivityStep(activity_id='activity-1'),
            PipelineActivityStep(activity_id='activity-2'),
            PipelineActivityStep(activity_id='activity-3'),
        ),
    )

    await repository.create(
        document=document,
        changelog_entry=entry(document, entry_id="entry-1"),
    )
    stored = await repository.get(
        workspace_id="workspace-1",
        pipeline_id=document.id,
    )

    assert stored == document


@pytest.mark.asyncio
async def test_list_filters_searches_orders_and_paginates(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """Active-first listing supports status, search, offset, and limit ten."""

    await create_workspace(workspace_id="workspace-1")
    await seed_activities(sqlite_database_path)
    repository = SqlitePipelineRepository(sqlite_database_path)
    for position in range(12):
        status = "disabled" if position == 11 else "active"
        document = replace(
            build_pipeline(pipeline_id=f"pipeline-{position:02d}"),
            title=f"Knowledge {position:02d}",
            status=status,
            updated_at=BASE_TIME + timedelta(seconds=position),
        )
        await repository.create(
            document=document,
            changelog_entry=entry(
                document,
                entry_id=f"entry-{position:02d}",
            ),
        )
    archived = replace(
        build_pipeline(pipeline_id="pipeline-archived"),
        title="Archived knowledge",
        status="archived",
    )
    await repository.create(
        document=archived,
        changelog_entry=entry(archived, entry_id="entry-archived"),
    )

    first, total = await repository.list(
        workspace_id="workspace-1",
        offset=0,
        limit=10,
        status=None,
        search="KNOWLEDGE",
    )
    second, second_total = await repository.list(
        workspace_id="workspace-1",
        offset=10,
        limit=10,
        status=None,
        search=None,
    )
    archived_items, archived_total = await repository.list(
        workspace_id="workspace-1",
        offset=0,
        limit=10,
        status="archived",
        search=None,
    )

    assert total == second_total == 12
    assert len(first) == 10
    assert len(second) == 2
    assert first[0].status == "active"
    assert second[-1].status == "disabled"
    assert archived_total == 1
    assert archived_items[0].id == "pipeline-archived"


@pytest.mark.asyncio
async def test_update_archive_and_changelog_are_atomic_resources(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """Updates replace steps, archival persists, and changelog is retained."""

    await create_workspace(workspace_id="workspace-1")
    await seed_activities(sqlite_database_path)
    repository = SqlitePipelineRepository(sqlite_database_path)
    original = build_pipeline()
    await repository.create(
        document=original,
        changelog_entry=entry(original, entry_id="entry-1"),
    )
    updated = replace(
        original,
        steps=(
            PipelineActivityStep(activity_id='activity-2'),
            PipelineActivityStep(activity_id='activity-1'),
        ),
        updated_at=BASE_TIME + timedelta(seconds=1),
    )
    archived = replace(
        updated,
        status="archived",
        updated_at=BASE_TIME + timedelta(seconds=2),
    )

    assert await repository.update(
        document=updated,
        changelog_entry=entry(
            updated,
            entry_id="entry-2",
            change_type="updated",
        ),
    )
    assert await repository.archive(
        document=archived,
        changelog_entry=entry(
            archived,
            entry_id="entry-3",
            change_type="archived",
        ),
    )
    entries, total = await repository.list_changelog(
        workspace_id="workspace-1",
        pipeline_id=original.id,
        offset=0,
        limit=10,
    )

    assert total == 3
    assert entries[0].change_type == "archived"
    assert await repository.get(
        workspace_id="workspace-1",
        pipeline_id=original.id,
    ) == archived
