"""Tests for user-owned persona operations."""

import pytest

from src.app.catalogs.persona_skills import InstructionOrigin
from src.app.services.personas import (
    PersonaCreate,
    PersonaService,
    PersonaUpdate,
)
from src.app.services.persona_skills import (
    DefinitionCreate,
    DefinitionNotFoundError,
    PersonaDefinitionService,
    SkillDefinitionService,
)
from src.app.services.users import UserNotFoundError
from tests.fakes.instruction_repository import (
    FakeInstructionRepository,
)
from tests.fakes.persona_skill_repository import (
    FakePersonaSkillRepository,
)
from tests.unit.services.instructions.test_service import seed_builtin


def build_persona_service(
    persona_definition_service: PersonaDefinitionService,
    skill_definition_service: SkillDefinitionService,
    persona_skill_repository: FakePersonaSkillRepository | None = None,
) -> PersonaService:
    """Build a Persona service with registered test identities."""

    return PersonaService(
        user_service=RegisteredUserService(),
        persona_definition_service=persona_definition_service,
        skill_definition_service=skill_definition_service,
        persona_skill_repository=(
            persona_skill_repository
            or FakePersonaSkillRepository()
        ),
    )


class RegisteredUserService:
    """Minimal user-profile boundary for user-owned Persona tests."""

    def __init__(self, registered_user_ids: set[str] | None = None) -> None:
        """Store identities that are allowed to own Personas."""

        self._registered_user_ids = registered_user_ids or {
            'user-1',
            'user-2',
        }

    async def get(self, *, user_id: str) -> object:
        """Return a placeholder profile or reject an unregistered user."""

        if user_id not in self._registered_user_ids:
            raise UserNotFoundError(user_id)
        return object()


@pytest.mark.asyncio
async def test_persona_crud_flow(
    persona_definition_service: PersonaDefinitionService,
    skill_definition_service: SkillDefinitionService,
) -> None:
    """Persona CRUD delegates to shared instruction behavior."""

    service = build_persona_service(
        persona_definition_service,
        skill_definition_service,
    )

    created = await service.create(
        user_id="user-1",
        payload=PersonaCreate(
            name="Tech Lead",
            description="Technical reviewer",
            instructions="Review architecture and implementation.",
        ),
    )

    assert created.instruction_type == "persona"
    assert created.workspace_id == "user-1"

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

    with pytest.raises(DefinitionNotFoundError):
        await service.describe(
            user_id="user-1",
            persona_id=created.id,
        )


@pytest.mark.asyncio
async def test_persona_service_sets_enabled_and_creates_content(
    persona_definition_service: PersonaDefinitionService,
    skill_definition_service: SkillDefinitionService,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """Persona-specific methods support PATCH and direct POST workflows."""

    service = build_persona_service(
        persona_definition_service,
        skill_definition_service,
    )
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
    persona_definition_service: PersonaDefinitionService,
    skill_definition_service: SkillDefinitionService,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """Persona writes create and replace ordered skill IDs."""

    association_repository = FakePersonaSkillRepository()
    service = build_persona_service(
        persona_definition_service,
        skill_definition_service,
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


@pytest.mark.asyncio
async def test_personas_are_isolated_between_users(
    persona_definition_service: PersonaDefinitionService,
    skill_definition_service: SkillDefinitionService,
) -> None:
    """Custom Personas are visible only to their owning user."""

    service = build_persona_service(
        persona_definition_service,
        skill_definition_service,
    )
    created = await service.create(
        user_id='user-1',
        payload=PersonaCreate(
            name='Private_reviewer',
            description='Private user Persona.',
            instructions='Review private work.',
        ),
    )

    assert (await service.list(user_id='user-2')).total == 0
    with pytest.raises(DefinitionNotFoundError):
        await service.describe(user_id='user-2', persona_id=created.id)


@pytest.mark.asyncio
async def test_builtin_persona_enablement_is_independent_per_user(
    persona_definition_service: PersonaDefinitionService,
    skill_definition_service: SkillDefinitionService,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """A built-in Persona setting for one user does not affect another user."""

    service = build_persona_service(
        persona_definition_service,
        skill_definition_service,
    )
    builtin = seed_builtin(instruction_repository, instruction_type='persona')

    await service.set_enabled(
        user_id='user-1',
        persona_id=builtin.id,
        enabled=False,
    )

    assert (await service.describe(user_id='user-1', persona_id=builtin.id)).enabled is False
    assert (await service.describe(user_id='user-2', persona_id=builtin.id)).enabled is True


@pytest.mark.asyncio
async def test_persona_operations_require_registered_user(
    persona_definition_service: PersonaDefinitionService,
    skill_definition_service: SkillDefinitionService,
) -> None:
    """Persona operations reject identities without user profiles."""

    service = build_persona_service(
        persona_definition_service,
        skill_definition_service,
    )

    with pytest.raises(UserNotFoundError):
        await service.list(user_id='missing-user')


@pytest.mark.asyncio
async def test_persona_rejects_skill_owned_by_another_user(
    persona_definition_service: PersonaDefinitionService,
    skill_definition_service: SkillDefinitionService,
) -> None:
    """Persona-Skill associations cannot cross user ownership boundaries."""

    service = build_persona_service(
        persona_definition_service,
        skill_definition_service,
    )
    foreign_skill = await skill_definition_service.create(
        workspace_id='user-2',
            payload=DefinitionCreate(
            name='Foreign_skill',
                description='Foreign user Skill.',
            instructions='A skill owned by user two.',
        ),
    )

    with pytest.raises(DefinitionNotFoundError):
        await service.create(
            user_id='user-1',
            payload=PersonaCreate(
                name='Cross_user_persona',
                description='Cross-user association attempt.',
                instructions='Attempt cross-user association.',
                skill_ids=(foreign_skill.id,),
            ),
        )






