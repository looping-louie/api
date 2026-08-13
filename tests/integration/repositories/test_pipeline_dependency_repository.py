"""Integration tests for pipeline-to-activity dependency lookup."""

from __future__ import annotations

from pathlib import Path

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
from tests.integration.repositories.test_sqlite_pipeline_repository import (
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
