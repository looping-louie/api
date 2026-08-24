"""Integration tests for SQL-backed catalog instruction pagination."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.app.catalogs.persona_skills import (
    CatalogInstructionCategory,
    CatalogInstructionSort,
    CatalogInstructionStatus,
)
from src.app.repositories.instructions.repository import (
    SqliteInstructionRepository,
)
from src.app.services.persona_skills import DefinitionDocument


WorkspaceFactory = Callable[..., Awaitable[None]]


def build_skill(index: int) -> DefinitionDocument:
    """Build a dated custom skill for deterministic page assertions."""

    created_at = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(
        minutes=index
    )
    category = (
        CatalogInstructionCategory.SECURITY_PRIVACY
        if index % 2 == 0
        else CatalogInstructionCategory.SALES
    )
    return DefinitionDocument(
        id=f"skill-{index:02d}",
        workspace_id="workspace-1",
        instruction_type="skill",
        name=f"Skill {29 - index:02d}",
        description="SQL pagination fixture.",
        instructions="Apply the skill.",
        metadata={"category": category.value},
        version=1,
        created_at=created_at,
        updated_at=created_at,
    )


@pytest.mark.asyncio
async def test_library_query_filters_sorts_and_pages_in_sql(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """A bounded page retains the total after SQL filters and ordering."""

    await create_workspace(workspace_id="workspace-1")
    repository = SqliteInstructionRepository(sqlite_database_path)

    for index in range(30):
        await repository.create(build_skill(index))

    page = await repository.list_available_for_workspace(
        workspace_id="workspace-1",
        instruction_type="skill",
        categories=(CatalogInstructionCategory.SECURITY_PRIVACY,),
        sort=CatalogInstructionSort.NEWEST,
        offset=3,
        limit=5,
    )
    empty_page = await repository.list_available_for_workspace(
        workspace_id="workspace-1",
        instruction_type="skill",
        categories=(CatalogInstructionCategory.SECURITY_PRIVACY,),
        sort=CatalogInstructionSort.NEWEST,
        offset=100,
        limit=5,
    )

    assert page.total == 15
    assert [item.id for item in page.items] == [
        "skill-22",
        "skill-20",
        "skill-18",
        "skill-16",
        "skill-14",
    ]
    assert empty_page.items == ()
    assert empty_page.total == 15


@pytest.mark.asyncio
async def test_library_query_filters_effective_workspace_status(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """Status filtering uses the effective workspace enablement override."""

    await create_workspace(workspace_id="workspace-1")
    repository = SqliteInstructionRepository(sqlite_database_path)

    for index in range(4):
        await repository.create(build_skill(index))

    changed = await repository.set_enabled(
        workspace_id="workspace-1",
        instruction_id="skill-02",
        enabled=False,
    )
    page = await repository.list_available_for_workspace(
        workspace_id="workspace-1",
        instruction_type="skill",
        status=CatalogInstructionStatus.DISABLED,
        categories=(CatalogInstructionCategory.SECURITY_PRIVACY,),
        limit=12,
    )

    assert changed is True
    assert page.total == 1
    assert [item.id for item in page.items] == ["skill-02"]
