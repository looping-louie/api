import pytest

from src.app.services.execution_instruction_library import (
    ExecutionInstructionLibraryService,
)
from src.app.services.instructions import build_assignment_instructions
from src.app.services.personas.service import (
    PersonaCreate,
    PersonaService,
)
from src.app.services.shared.instruction import (
    InstructionCreate,
    InstructionService,
    InstructionUpdate,
)
from src.app.services.shared.tenant import TenantService
from src.app.services.skills.service import SkillService
from tests.fakes.instruction_repository import FakeInstructionRepository
from tests.fakes.persona_skill_repository import (
    FakePersonaSkillRepository,
)


@pytest.mark.asyncio
async def test_api_custom_is_immediately_available_to_execution(
    instruction_service: InstructionService,
    instruction_repository: FakeInstructionRepository,
    tenant_service: TenantService,
) -> None:
    persona_skill_repository = FakePersonaSkillRepository()
    skill_service = SkillService(
        tenant_service=tenant_service,
        instruction_service=instruction_service,
    )
    persona_service = PersonaService(
        tenant_service=tenant_service,
        instruction_service=instruction_service,
        persona_skill_repository=persona_skill_repository,
    )
    runtime_service = ExecutionInstructionLibraryService(
        repository=instruction_repository,
        persona_skill_repository=persona_skill_repository,
        tenant_service=tenant_service,
    )
    skill = await skill_service.create(
        user_id="user-1",
        payload=InstructionCreate(
            name="Workspace Security",
            description="Custom security checks.",
            instructions="SQL skill content version one.",
        ),
    )
    persona = await persona_service.create(
        user_id="user-1",
        payload=PersonaCreate(
            name="Workspace Lead",
            description="Custom technical lead.",
            instructions="SQL persona content.",
            skill_ids=(skill.id,),
        ),
    )

    library = await runtime_service.load(user_id="user-1")

    assert library.skill_contents([skill.id]) == [
        "SQL skill content version one.",
    ]
    assert library.persona_content(persona.id) == (
        "SQL persona content."
    )
    assert skill.id in {
        entry["id"]
        for entry in library.skill_registry()
    }
    assert persona.id in {
        entry["id"]
        for entry in library.persona_registry()
    }
    persona_registry_entry = next(
        entry
        for entry in library.persona_registry()
        if entry["id"] == persona.id
    )
    assert persona_registry_entry["skills"] == [skill.id]
    snapshot_entries = {
        entry["id"]: entry
        for entry in library.snapshot()["instructions"]
    }
    skill_snapshot = snapshot_entries[skill.id]
    persona_snapshot = snapshot_entries[persona.id]

    assert skill_snapshot["instruction_type"] == "skill"
    assert skill_snapshot["origin"] == "custom"
    assert skill_snapshot["version"] == 1
    assert skill_snapshot["catalog_version"] is None
    assert skill_snapshot["content"] == (
        "SQL skill content version one."
    )
    assert skill_snapshot["metadata"] == {}
    assert persona_snapshot["instruction_type"] == "persona"
    assert persona_snapshot["content"] == "SQL persona content."
    assert persona_snapshot["skill_ids"] == [skill.id]


@pytest.mark.asyncio
async def test_fresh_execution_read_reflects_sql_update(
    instruction_service: InstructionService,
    instruction_repository: FakeInstructionRepository,
    tenant_service: TenantService,
) -> None:
    persona_skill_repository = FakePersonaSkillRepository()
    skill_service = SkillService(
        tenant_service=tenant_service,
        instruction_service=instruction_service,
    )
    runtime_service = ExecutionInstructionLibraryService(
        repository=instruction_repository,
        persona_skill_repository=persona_skill_repository,
        tenant_service=tenant_service,
    )
    skill = await skill_service.create(
        user_id="user-1",
        payload=InstructionCreate(
            name="Mutable Runtime Skill",
            description="Loaded from SQL.",
            instructions="SQL content before update.",
        ),
    )
    before = await runtime_service.load(user_id="user-1")

    await skill_service.update(
        user_id="user-1",
        skill_id=skill.id,
        payload=InstructionUpdate(
            expected_version=1,
            instructions="SQL content after update.",
        ),
    )
    after = await runtime_service.load(user_id="user-1")

    assert before.skill_contents([skill.id]) == [
        "SQL content before update.",
    ]
    assert after.skill_contents([skill.id]) == [
        "SQL content after update.",
    ]
    before_snapshot = {
        entry["id"]: entry
        for entry in before.snapshot()["instructions"]
    }
    after_snapshot = {
        entry["id"]: entry
        for entry in after.snapshot()["instructions"]
    }

    assert before_snapshot[skill.id]["version"] == 1
    assert before_snapshot[skill.id]["content"] == (
        "SQL content before update."
    )
    assert after_snapshot[skill.id]["version"] == 2
    assert after_snapshot[skill.id]["content"] == (
        "SQL content after update."
    )


def test_assignment_builder_only_uses_resolved_content() -> None:
    prompt = build_assignment_instructions(
        role="reviewer",
        persona_content="Resolved persona from SQL.",
        skill_contents=[
            "Resolved skill one.",
            "Resolved skill two.",
        ],
        focus="Review the result.",
    )

    assert "Resolved persona from SQL." in prompt
    assert "Resolved skill one." in prompt
    assert "Resolved skill two." in prompt
    assert "Review the result." in prompt
