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

    await create_workspace(workspace_id="workspace-1")
    await seed_activities(sqlite_database_path)
    document = build_pipeline()
    await SqlitePipelineRepository(sqlite_database_path).create(
        document=document,
        changelog_entry=entry(document, entry_id="pipeline-entry"),
    )

    usages = await SqliteDependencyRepository(
        sqlite_database_path
    ).find_usages(
        workspace_id="workspace-1",
        target=ResourceReference("activity", "activity-1"),
    )

    assert len(usages) == 1
    assert usages[0].source == ResourceReference(
        "pipeline",
        "pipeline-1",
    )
    assert usages[0].relation == "activity"


@pytest.mark.asyncio
async def test_finds_linked_service_usage_in_execution_model_targets(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """Linked services remain protected by every persisted model-target scope."""

    await create_workspace(workspace_id="workspace-1")
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
            """
            INSERT INTO workspace_execution_defaults (
                workspace_id, model_target_json, harness_json, updated_at
            ) VALUES (?, ?, NULL, ?)
            """,
            ("workspace-1", target, "2026-08-25T00:00:00+00:00"),
        )
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
        workspace_id="workspace-1",
        target=ResourceReference("linked_service", "linked-service-1"),
    )

    assert {(usage.source, usage.relation) for usage in usages} == {
        (ResourceReference("workspace", "workspace-1"), "model_target"),
        (ResourceReference("pipeline", "pipeline-1"), "model_target"),
        (ResourceReference("activity", "activity-1"), "model_target"),
        (ResourceReference("activity", "activity-1"), "agent_model_target"),
    }
