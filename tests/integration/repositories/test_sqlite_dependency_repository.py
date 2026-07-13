"""Integration tests for SqliteDependencyRepository."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from src.app.services.shared.reference_resolver import ResourceReference
from src.app.repositories.composition_repository import (
    SqliteCompositionRepository,
)
from src.app.repositories.dependency_repository import (
    SqliteDependencyRepository,
)
from tests.integration.factories import build_composition


WorkspaceFactory = Callable[..., Awaitable[None]]


@pytest.mark.asyncio
async def test_finds_council_instruction_dependencies(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    composition_repository = SqliteCompositionRepository(
        sqlite_database_path,
    )
    dependency_repository = SqliteDependencyRepository(
        sqlite_database_path,
    )

    await composition_repository.create(
        build_composition(
            composition_id="council-1",
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

    persona_usages = await dependency_repository.find_usages(
        workspace_id="workspace-1",
        target=ResourceReference(
            resource_type="persona",
            resource_id="persona-1",
        ),
    )
    skill_usages = await dependency_repository.find_usages(
        workspace_id="workspace-1",
        target=ResourceReference(
            resource_type="skill",
            resource_id="skill-1",
        ),
    )

    assert len(persona_usages) == 1
    assert persona_usages[0].source.resource_type == "council"
    assert persona_usages[0].source.resource_id == "council-1"
    assert persona_usages[0].relation == "assignment_persona"

    assert len(skill_usages) == 1
    assert skill_usages[0].source.resource_type == "council"
    assert skill_usages[0].source.resource_id == "council-1"
    assert skill_usages[0].relation == "assignment_skill"


@pytest.mark.asyncio
async def test_finds_loop_council_and_model_dependencies(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    composition_repository = SqliteCompositionRepository(
        sqlite_database_path,
    )
    dependency_repository = SqliteDependencyRepository(
        sqlite_database_path,
    )

    await composition_repository.create(
        build_composition(
            composition_id="loop-1",
            composition_type="loop",
            name="Production Loop",
            attributes={
                "council_id": "council-1",
                "max_iterations": 3,
            },
            items=(
                {
                    "role": "generator",
                    "model_id": "kimi-k2.6",
                },
            ),
        )
    )

    council_usages = await dependency_repository.find_usages(
        workspace_id="workspace-1",
        target=ResourceReference(
            resource_type="council",
            resource_id="council-1",
        ),
    )
    model_usages = await dependency_repository.find_usages(
        workspace_id="workspace-1",
        target=ResourceReference(
            resource_type="model",
            resource_id="kimi-k2.6",
        ),
    )

    assert len(council_usages) == 1
    assert council_usages[0].source.resource_id == "loop-1"
    assert council_usages[0].relation == "loop_council"

    assert len(model_usages) == 1
    assert model_usages[0].source.resource_id == "loop-1"
    assert model_usages[0].relation == "model_binding"


@pytest.mark.asyncio
async def test_returns_empty_for_unused_resource(
    sqlite_database_path: Path,
) -> None:
    repository = SqliteDependencyRepository(
        sqlite_database_path,
    )

    usages = await repository.find_usages(
        workspace_id="workspace-1",
        target=ResourceReference(
            resource_type="persona",
            resource_id="missing-persona",
        ),
    )

    assert usages == []
