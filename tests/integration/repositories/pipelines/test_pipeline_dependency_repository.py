"""Integration tests for pipeline-to-activity dependency lookup."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from src.app.repositories.pipelines.sqlite_repository import (
    SqlitePipelineRepository,
)
from src.app.repositories.shared.dependency_repository import (
    SqliteDependencyRepository,
)
from src.app.services.shared.reference_resolver import ResourceReference
from tests.factories.pipelines import build_pipeline
from tests.integration.conftest import WorkspaceFactory
from tests.integration.repositories.pipelines.test_sqlite_pipeline_repository import (
    entry,
    seed_activities,
)


@pytest.mark.asyncio
async def test_finds_pipeline_usage_of_activity(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """A stored pipeline reports a blocking activity reference."""

    await create_workspace(project_id="workspace-1")
    await seed_activities(sqlite_database_path)
    document = build_pipeline()
    await SqlitePipelineRepository(sqlite_database_path).create(
        document=document,
        changelog_entry=entry(document, entry_id="pipeline-entry"),
    )

    usages = await SqliteDependencyRepository(
        sqlite_database_path
    ).find_usages(
        project_id="workspace-1",
        target=ResourceReference("activity", "activity-1"),
    )

    assert len(usages) == 1
    assert usages[0].source == ResourceReference(
        "pipeline",
        "pipeline-1",
    )
    assert usages[0].relation == "activity"


@pytest.mark.asyncio
async def test_does_not_block_linked_service_deletion_for_definition_models(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """Logical model definitions do not retain linked-service dependencies."""

    await create_workspace(project_id="workspace-1")
    await seed_activities(sqlite_database_path)
    document = build_pipeline()
    await SqlitePipelineRepository(sqlite_database_path).create(
        document=document,
        changelog_entry=entry(document, entry_id="pipeline-entry"),
    )
    target = '{"linked_service_id":"linked-service-1","model_id":"model-1"}'
    agent_config = (
        '{"agents":[{"persona_id":"persona-1","role":"generator",'
        '"model_target":{"linked_service_id":"linked-service-1",'
        '"model_id":"model-1"}}]}'
    )

    async with aiosqlite.connect(sqlite_database_path) as connection:
        await connection.execute(
            "UPDATE pipelines SET model_target_json = ? WHERE id = ?",
            (target, "pipeline-1"),
        )
        await connection.execute(
            """
            UPDATE activities
            SET model_target_json = ?, config_json = ?
            WHERE id = ?
            """,
            (target, agent_config, "activity-1"),
        )
        await connection.commit()

    usages = await SqliteDependencyRepository(
        sqlite_database_path
    ).find_usages(
        project_id="workspace-1",
        target=ResourceReference("linked_service", "linked-service-1"),
    )

    assert usages == []
