"""Integration tests for SqliteInstructionRepository."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite
import pytest

from src.app.repositories.instructions.instruction_repository import (
    SqliteInstructionRepository,
)
from src.app.services.shared.instruction import (
    InstructionDocument,
    InstructionType,
)


WorkspaceFactory = Callable[..., Awaitable[None]]


def build_instruction(
    *,
    instruction_id: str = "instruction-1",
    workspace_id: str = "workspace-1",
    instruction_type: InstructionType = "persona",
    name: str = "Security Reviewer",
    description: str = "Reviews security concerns.",
    instructions: str = "Review the supplied work for security issues.",
    metadata: Mapping[str, Any] | None = None,
    version: int = 1,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> InstructionDocument:
    """Build one instruction document for integration tests."""

    created = created_at or datetime(
        2026,
        7,
        13,
        10,
        0,
        tzinfo=UTC,
    )

    return InstructionDocument(
        id=instruction_id,
        workspace_id=workspace_id,
        instruction_type=instruction_type,
        name=name,
        description=description,
        instructions=instructions,
        metadata=dict(
            metadata
            or {
                "category": "security",
            }
        ),
        version=version,
        created_at=created,
        updated_at=updated_at or created,
    )


@pytest.mark.asyncio
async def test_create_get_and_list_instruction(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    repository = SqliteInstructionRepository(
        sqlite_database_path,
    )
    document = build_instruction()

    created = await repository.create(
        document,
    )
    stored = await repository.get(
        workspace_id="workspace-1",
        instruction_type="persona",
        instruction_id="instruction-1",
    )
    summaries = await repository.list_summaries(
        workspace_id="workspace-1",
        instruction_type="persona",
    )

    assert created == document
    assert stored == document

    assert len(summaries) == 1
    assert summaries[0].id == document.id
    assert summaries[0].name == document.name
    assert summaries[0].description == document.description
    assert summaries[0].version == 1


@pytest.mark.asyncio
async def test_repository_preserves_metadata_and_datetimes(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    repository = SqliteInstructionRepository(
        sqlite_database_path,
    )
    document = build_instruction(
        metadata={
            "applies_when": [
                "python",
                "fastapi",
            ],
            "default_strictness": {
                "prototype": 30,
                "mvp": 60,
                "production": 90,
            },
        },
    )

    await repository.create(
        document,
    )
    stored = await repository.get(
        workspace_id="workspace-1",
        instruction_type="persona",
        instruction_id="instruction-1",
    )

    assert stored is not None
    assert stored.metadata == document.metadata
    assert stored.created_at == document.created_at
    assert stored.updated_at == document.updated_at


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
    repository = SqliteInstructionRepository(
        sqlite_database_path,
    )

    await repository.create(
        build_instruction(
            instruction_id="persona-workspace-1",
            workspace_id="workspace-1",
            instruction_type="persona",
            name="Reviewer",
        )
    )
    await repository.create(
        build_instruction(
            instruction_id="skill-workspace-1",
            workspace_id="workspace-1",
            instruction_type="skill",
            name="Reviewer",
        )
    )
    await repository.create(
        build_instruction(
            instruction_id="persona-workspace-2",
            workspace_id="workspace-2",
            instruction_type="persona",
            name="Reviewer",
        )
    )

    summaries = await repository.list_summaries(
        workspace_id="workspace-1",
        instruction_type="persona",
    )
    wrong_workspace = await repository.get(
        workspace_id="workspace-2",
        instruction_type="persona",
        instruction_id="persona-workspace-1",
    )
    wrong_type = await repository.get(
        workspace_id="workspace-1",
        instruction_type="skill",
        instruction_id="persona-workspace-1",
    )

    assert [
        summary.id
        for summary in summaries
    ] == [
        "persona-workspace-1",
    ]
    assert wrong_workspace is None
    assert wrong_type is None


@pytest.mark.asyncio
async def test_list_summaries_orders_by_normalized_name(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    repository = SqliteInstructionRepository(
        sqlite_database_path,
    )

    await repository.create(
        build_instruction(
            instruction_id="instruction-zulu",
            name="Zulu Reviewer",
        )
    )
    await repository.create(
        build_instruction(
            instruction_id="instruction-alpha",
            name="  Alpha Reviewer  ",
        )
    )

    summaries = await repository.list_summaries(
        workspace_id="workspace-1",
        instruction_type="persona",
    )

    assert [
        summary.id
        for summary in summaries
    ] == [
        "instruction-alpha",
        "instruction-zulu",
    ]


@pytest.mark.asyncio
async def test_update_uses_optimistic_concurrency(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    repository = SqliteInstructionRepository(
        sqlite_database_path,
    )
    original = build_instruction()

    await repository.create(
        original,
    )

    updated = replace(
        original,
        name="Updated Security Reviewer",
        description="Updated description.",
        instructions="Updated instructions.",
        version=2,
        updated_at=original.updated_at + timedelta(minutes=5),
    )

    stored = await repository.update(
        updated,
        expected_version=1,
    )

    assert stored == updated

    stale_update = replace(
        updated,
        instructions="Stale instructions.",
        version=3,
        updated_at=updated.updated_at + timedelta(minutes=5),
    )

    stale_result = await repository.update(
        stale_update,
        expected_version=1,
    )
    current = await repository.get(
        workspace_id="workspace-1",
        instruction_type="persona",
        instruction_id="instruction-1",
    )

    assert stale_result is None
    assert current == updated


@pytest.mark.asyncio
async def test_delete_removes_instruction(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    repository = SqliteInstructionRepository(
        sqlite_database_path,
    )
    document = build_instruction()

    await repository.create(
        document,
    )

    deleted = await repository.delete(
        workspace_id="workspace-1",
        instruction_type="persona",
        instruction_id="instruction-1",
    )
    deleted_again = await repository.delete(
        workspace_id="workspace-1",
        instruction_type="persona",
        instruction_id="instruction-1",
    )
    stored = await repository.get(
        workspace_id="workspace-1",
        instruction_type="persona",
        instruction_id="instruction-1",
    )

    assert deleted is True
    assert deleted_again is False
    assert stored is None


@pytest.mark.asyncio
async def test_database_rejects_duplicate_normalized_name(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    await create_workspace(
        workspace_id="workspace-1",
    )
    repository = SqliteInstructionRepository(
        sqlite_database_path,
    )

    await repository.create(
        build_instruction(
            instruction_id="instruction-1",
            name="Code Review",
        )
    )

    duplicate = build_instruction(
        instruction_id="instruction-2",
        name="  code   review  ",
    )

    with pytest.raises(aiosqlite.IntegrityError):
        await repository.create(
            duplicate,
        )
