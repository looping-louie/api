"""Integration tests for SqliteValidationRepository."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from src.app.repositories.instructions.repository import (
    SqliteInstructionRepository,
)
from src.app.repositories.shared.validation_repository import (
    SqliteValidationRepository,
)
from tests.integration.factories import build_instruction


WorkspaceFactory = Callable[..., Awaitable[None]]


@pytest.mark.asyncio
async def test_finds_instruction_by_normalized_name(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """Find a custom instruction using its normalized display name."""

    await create_workspace(
        workspace_id="workspace-1",
    )
    instruction_repository = SqliteInstructionRepository(
        sqlite_database_path,
    )
    validation_repository = SqliteValidationRepository(
        sqlite_database_path,
    )

    await instruction_repository.create(
        build_instruction(
            instruction_id="persona-1",
            name="  Security   Reviewer ",
        )
    )

    resource_id = await validation_repository.find_resource_id_by_name(
        workspace_id="workspace-1",
        resource_type="persona",
        normalized_name="security reviewer",
    )

    assert resource_id == "persona-1"


@pytest.mark.asyncio
async def test_name_lookup_isolated_by_workspace_and_type(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """Keep normalized name lookups isolated by workspace and type."""

    await create_workspace(
        workspace_id="workspace-1",
    )
    await create_workspace(
        workspace_id="workspace-2",
    )
    instruction_repository = SqliteInstructionRepository(
        sqlite_database_path,
    )
    validation_repository = SqliteValidationRepository(
        sqlite_database_path,
    )

    await instruction_repository.create(
        build_instruction(
            instruction_id="persona-1",
            workspace_id="workspace-1",
            instruction_type="persona",
            name="Reviewer",
        )
    )

    wrong_workspace = await validation_repository.find_resource_id_by_name(
        workspace_id="workspace-2",
        resource_type="persona",
        normalized_name="reviewer",
    )
    wrong_type = await validation_repository.find_resource_id_by_name(
        workspace_id="workspace-1",
        resource_type="skill",
        normalized_name="reviewer",
    )

    assert wrong_workspace is None
    assert wrong_type is None
