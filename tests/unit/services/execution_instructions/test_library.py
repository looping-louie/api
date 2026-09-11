"""Tests for immutable execution instruction libraries."""

import pytest

from src.app.services.execution_instructions import (
    ExecutionInstructionLibraryService,
)
from src.app.services.personas import (
    PersonaCreate,
    PersonaService,
)
from src.app.services.persona_skills import (
    DefinitionCreate,
    DefinitionUpdate,
    PersonaDefinitionService,
    SkillDefinitionService,
)
from src.app.services.shared.tenant import TenantService
from src.app.services.skills import SkillService
from tests.fakes.instruction_repository import FakeInstructionRepository
from tests.fakes.persona_skill_repository import (
    FakePersonaSkillRepository,
)


class RegisteredUserService:
    """Minimal registered-user boundary for user-owned Skill tests."""

    async def get(self, *, user_id: str) -> object:
        """Accept the registered test identity."""

        assert user_id == 'user-1'
        return object()


@pytest.mark.asyncio
async def test_user_persona_and_ordered_skills_are_available_to_execution(
    persona_definition_service: PersonaDefinitionService,
    skill_definition_service: SkillDefinitionService,
    instruction_repository: FakeInstructionRepository,
    tenant_service: TenantService,
) -> None:
    """The execution snapshot resolves a user's Persona and linked Skills."""

    persona_skill_repository = FakePersonaSkillRepository()
    skill_service = SkillService(
        user_service=RegisteredUserService(),
        skill_definition_service=skill_definition_service,
    )
    persona_service = PersonaService(
        user_service=RegisteredUserService(),
        persona_definition_service=persona_definition_service,
        skill_definition_service=skill_definition_service,
        persona_skill_repository=persona_skill_repository,
    )
    runtime_service = ExecutionInstructionLibraryService(
        repository=instruction_repository,
        persona_repository=instruction_repository,
        persona_skill_repository=persona_skill_repository,
        tenant_service=tenant_service,
    )
    skill = await skill_service.create(
        user_id="user-1",
        payload=DefinitionCreate(
            name="Project Security",
            description="Custom security checks.",
            instructions="SQL skill content version one.",
        ),
    )
    persona = await persona_service.create(
        user_id="user-1",
        payload=PersonaCreate(
            name="Project Lead",
            description="Custom technical lead.",
            instructions="SQL persona content.",
            skill_ids=(skill.id,),
        ),
    )

    library = await runtime_service.load(user_id="user-1")

    assert library.persona_content(persona.id) == (
        "SQL persona content."
    )
    snapshot_entries = {
        entry["id"]: entry
        for entry in library.snapshot()["instructions"]
    }
    persona_snapshot = snapshot_entries[persona.id]

    agent_snapshot = library.agent_snapshot(persona.id)

    assert snapshot_entries[skill.id]["content"] == "SQL skill content version one."
    assert persona_snapshot["instruction_type"] == "persona"
    assert persona_snapshot["content"] == "SQL persona content."
    assert persona_snapshot["skill_ids"] == [skill.id]
    assert agent_snapshot["persona"]["id"] == persona.id
    assert [entry["id"] for entry in agent_snapshot["skills"]] == [skill.id]
    assert agent_snapshot["skills"][0]["version"] == 1


@pytest.mark.asyncio
async def test_user_owned_skill_update_is_visible_to_its_owner(
    skill_definition_service: SkillDefinitionService,
    instruction_repository: FakeInstructionRepository,
    tenant_service: TenantService,
) -> None:
    """An updated user-owned Skill exposes its current persisted version."""

    persona_skill_repository = FakePersonaSkillRepository()
    skill_service = SkillService(
        user_service=RegisteredUserService(),
        skill_definition_service=skill_definition_service,
    )
    skill = await skill_service.create(
        user_id="user-1",
        payload=DefinitionCreate(
            name="Mutable Runtime Skill",
            description="Loaded from SQL.",
            instructions="SQL content before update.",
        ),
    )
    await skill_service.update(
        user_id="user-1",
        skill_id=skill.id,
        payload=DefinitionUpdate(
            expected_version=1,
            instructions="SQL content after update.",
        ),
    )
    updated = await skill_service.describe(
        user_id='user-1',
        skill_id=skill.id,
    )

    assert updated.version == 2
    assert updated.instructions == 'SQL content after update.'
