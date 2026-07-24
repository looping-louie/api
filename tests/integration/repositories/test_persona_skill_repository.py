"""Integration tests for SQLite persona-skill persistence."""

from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from src.app.repositories.instruction_repository import (
    SqliteInstructionRepository,
)
from src.app.repositories.persona_skill_repository import (
    SqlitePersonaSkillRepository,
)
from tests.integration.repositories.test_sqlite_instruction_repository import (
    build_instruction,
)


WorkspaceFactory = Callable[..., Awaitable[None]]


@pytest.mark.asyncio
async def test_repository_replaces_and_orders_persona_skills(
    sqlite_database_path: Path,
    create_workspace: WorkspaceFactory,
) -> None:
    """Replacing associations preserves order and supports clearing."""

    await create_workspace(workspace_id="workspace-1")
    instruction_repository = SqliteInstructionRepository(
        sqlite_database_path,
    )
    association_repository = SqlitePersonaSkillRepository(
        sqlite_database_path,
    )
    persona = build_instruction(
        instruction_id="persona-1",
        instruction_type="persona",
        name="Reviewer",
    )
    first_skill = build_instruction(
        instruction_id="skill-1",
        instruction_type="skill",
        name="Security",
    )
    second_skill = build_instruction(
        instruction_id="skill-2",
        instruction_type="skill",
        name="Privacy",
    )

    for document in (persona, first_skill, second_skill):
        await instruction_repository.create(document)

    await association_repository.replace_for_persona(
        persona_id=persona.id,
        skill_ids=(second_skill.id, first_skill.id),
    )
    stored = await association_repository.list_for_persona(
        persona_id=persona.id,
    )
    deleted = await instruction_repository.delete(
        workspace_id="workspace-1",
        instruction_type="skill",
        instruction_id=second_skill.id,
    )
    after_delete = await association_repository.list_for_persona(
        persona_id=persona.id,
    )
    await association_repository.replace_for_persona(
        persona_id=persona.id,
        skill_ids=(),
    )

    assert stored == (second_skill.id, first_skill.id)
    assert deleted is True
    assert after_delete == (first_skill.id,)
    assert await association_repository.list_for_persona(
        persona_id=persona.id,
    ) == ()
