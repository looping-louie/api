"""Tests for workspace-aware persona operations."""

import pytest

from src.app.catalogs.instructions import InstructionOrigin
from src.app.services.personas.service import (
    PersonaCreate,
    PersonaService,
    PersonaUpdate,
)
from src.app.services.instructions import (
    InstructionNotFoundError,
    InstructionService,
)
from src.app.services.shared.tenant import (
    TenantService,
    WorkspaceMembership,
)
from tests.fakes.tenant_repository import FakeTenantRepository
from tests.fakes.instruction_repository import (
    FakeInstructionRepository,
)
from tests.fakes.persona_skill_repository import (
    FakePersonaSkillRepository,
)
from tests.services.test_instruction_service import seed_builtin


def build_persona_service(
    instruction_service: InstructionService,
    persona_skill_repository: FakePersonaSkillRepository | None = None,
) -> PersonaService:
    """Build a persona service with one default workspace membership."""

    repository = FakeTenantRepository(
        [
            WorkspaceMembership(
                user_id="user-1",
                workspace_id="workspace-1",
                is_default=True,
            ),
        ]
    )

    return PersonaService(
        tenant_service=TenantService(repository=repository),
        instruction_service=instruction_service,
        persona_skill_repository=(
            persona_skill_repository
            or FakePersonaSkillRepository()
        ),
    )


@pytest.mark.asyncio
async def test_persona_crud_flow(
    instruction_service: InstructionService,
) -> None:
    """Persona CRUD delegates to shared instruction behavior."""

    service = build_persona_service(instruction_service)

    created = await service.create(
        user_id="user-1",
        payload=PersonaCreate(
            name="Tech Lead",
            description="Technical reviewer",
            instructions="Review architecture and implementation.",
        ),
    )

    assert created.instruction_type == "persona"
    assert created.workspace_id == "workspace-1"

    summaries = await service.list(user_id="user-1")

    assert len(summaries) == 1
    assert summaries[0].id == created.id

    described = await service.describe(
        user_id="user-1",
        persona_id=created.id,
    )

    assert described.id == created.id
    assert described.origin == InstructionOrigin.CUSTOM
    assert described.instructions == created.instructions

    updated = await service.update(
        user_id="user-1",
        persona_id=created.id,
        payload=PersonaUpdate(
            expected_version=1,
            description="Senior technical reviewer",
        ),
    )

    assert updated.description == "Senior technical reviewer"
    assert updated.version == 2

    await service.delete(
        user_id="user-1",
        persona_id=created.id,
    )

    with pytest.raises(InstructionNotFoundError):
        await service.describe(
            user_id="user-1",
            persona_id=created.id,
        )


@pytest.mark.asyncio
async def test_persona_service_sets_enabled_and_creates_content(
    instruction_service: InstructionService,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """Persona-specific methods support PATCH and direct POST workflows."""

    service = build_persona_service(instruction_service)
    builtin = seed_builtin(
        instruction_repository,
        instruction_type="persona",
    )

    disabled = await service.set_enabled(
        user_id="user-1",
        persona_id=builtin.id,
        enabled=False,
    )
    enabled = await service.set_enabled(
        user_id="user-1",
        persona_id=builtin.id,
        enabled=True,
    )
    created = await service.create(
        user_id="user-1",
        payload=PersonaCreate(
            name="Workspace Lead",
            description=builtin.description,
            instructions=builtin.instructions,
            metadata=builtin.metadata,
        ),
    )

    assert disabled.enabled is False
    assert enabled.enabled is True
    assert created.source_instruction_id is None


@pytest.mark.asyncio
async def test_persona_service_manages_skill_associations(
    instruction_service: InstructionService,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """Persona writes create and replace ordered skill IDs."""

    association_repository = FakePersonaSkillRepository()
    service = build_persona_service(
        instruction_service,
        association_repository,
    )
    skill = seed_builtin(
        instruction_repository,
        instruction_type="skill",
    )
    source = seed_builtin(
        instruction_repository,
        instruction_type="persona",
    )
    await association_repository.replace_for_persona(
        persona_id=source.id,
        skill_ids=(skill.id,),
    )

    created = await service.create(
        user_id="user-1",
        payload=PersonaCreate(
            name="Associated reviewer",
            description="Reviews with one skill.",
            instructions="Review the work.",
            skill_ids=(skill.id,),
        ),
    )
    updated = await service.update(
        user_id="user-1",
        persona_id=created.id,
        payload=PersonaUpdate(
            expected_version=1,
            skill_ids=(),
        ),
    )
    assert created.skill_ids == (skill.id,)
    assert updated.skill_ids == ()
