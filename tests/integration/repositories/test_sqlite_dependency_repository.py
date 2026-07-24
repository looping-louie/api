"""Integration tests for loop persona dependency lookup."""

from pathlib import Path

import pytest

from src.app.repositories.shared.dependency_repository import (
    SqliteDependencyRepository,
)
from src.app.repositories.loops.sqlite_loop_repository import (
    SqliteLoopRepository,
)
from src.app.services.shared.reference_resolver import ResourceReference
from tests.integration.conftest import WorkspaceFactory
from tests.integration.repositories.test_sqlite_loop_repository import (
    entry,
    loop_document,
)


@pytest.mark.asyncio
async def test_finds_persona_usage_from_loop_agents(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """A loop agent blocks deletion of its referenced persona."""

    await create_workspace(workspace_id="workspace-1")
    document = loop_document()
    await SqliteLoopRepository(sqlite_database_path).create(
        document=document,
        changelog_entry=entry(document, entry_id="entry-1"),
    )
    repository = SqliteDependencyRepository(sqlite_database_path)

    usages = await repository.find_usages(
        workspace_id="workspace-1",
        target=ResourceReference("persona", "persona-1"),
    )
    unrelated = await repository.find_usages(
        workspace_id="workspace-1",
        target=ResourceReference("skill", "skill-1"),
    )

    assert len(usages) == 1
    assert usages[0].source == ResourceReference("loop", "loop-1")
    assert usages[0].relation == "persona"
    assert unrelated == []
