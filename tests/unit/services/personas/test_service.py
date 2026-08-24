"""Tests for workspace-aware persona operations."""

import pytest

from src.app.catalogs.persona_skills import InstructionOrigin
from src.app.services.personas import (
    PersonaCreate,
    PersonaLinkedServiceSelection,
    PersonaService,
    PersonaUpdate,
)
from src.app.services.persona_skills import (
    DefinitionNotFoundError,
    PersonaDefinitionService,
    SkillDefinitionService,
)
from src.app.services.shared.tenant import (
    TenantService,
    WorkspaceMembership,
)
from src.app.services.shared.reference_resolver import ReferenceResolver
from tests.fakes.tenant_repository import FakeTenantRepository
from tests.fakes.instruction_repository import (
    FakeInstructionRepository,
)
from tests.fakes.persona_skill_repository import (
    FakePersonaSkillRepository,
)
from tests.fakes.persona_linked_service_selection_repository import (
    FakePersonaLinkedServiceSelectionRepository,
)
from tests.fakes.reference_repository import FakeReferenceRepository
from tests.unit.services.instructions.test_service import seed_builtin


class FakeLinkedServiceSelectionValidator:
    """Capture persona linked-service selection validation calls."""

    def __init__(self) -> None:
        """Initialize an empty validation call log."""

        self.calls: list[tuple[str, str, str]] = []

    async def require_available_selection(
        self,
        *,
        workspace_id: str,
        service_id: str,
        model_id: str,
    ) -> None:
        """Record the selection that persona creation asks to validate."""

        self.calls.append((workspace_id, service_id, model_id))


def build_persona_service(
    persona_definition_service: PersonaDefinitionService,
    skill_definition_service: SkillDefinitionService,
    persona_skill_repository: FakePersonaSkillRepository | None = None,
    persona_linked_service_selection_repository: (
        FakePersonaLinkedServiceSelectionRepository | None
    ) = None,
    reference_repository: FakeReferenceRepository | None = None,
    linked_service_service: FakeLinkedServiceSelectionValidator | None = None,
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
        persona_definition_service=persona_definition_service,
        skill_definition_service=skill_definition_service,
        persona_skill_repository=(
            persona_skill_repository
            or FakePersonaSkillRepository()
        ),
        persona_linked_service_selection_repository=(
            persona_linked_service_selection_repository
            or FakePersonaLinkedServiceSelectionRepository()
        ),
        linked_service_service=(
            linked_service_service or FakeLinkedServiceSelectionValidator()
        ),
        reference_resolver=ReferenceResolver(
            repository=reference_repository or FakeReferenceRepository(),
        ),
    )


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

    selection = PersonaLinkedServiceSelection(
        linked_service_id='linked-service-1',
        model_id='service-model',
    )
    created = await service.create(
        user_id="user-1",
        payload=PersonaCreate(
            name="Tech Lead",
            description="Technical reviewer",
            instructions="Review architecture and implementation.",
            linked_service_selection=selection,
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
            linked_service_selection=PersonaLinkedServiceSelection(
                linked_service_id='linked-service-1',
                model_id='service-model',
            ),
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
            linked_service_selection=PersonaLinkedServiceSelection(
                linked_service_id='linked-service-1',
                model_id='service-model',
            ),
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
@pytest.mark.asyncio
async def test_persona_service_persists_validated_linked_service_selection(
    persona_definition_service: PersonaDefinitionService,
    skill_definition_service: SkillDefinitionService,
) -> None:
    """New selections coexist with the legacy persona model association."""

    validator = FakeLinkedServiceSelectionValidator()
    service = build_persona_service(
        persona_definition_service,
        skill_definition_service,
        linked_service_service=validator,
    )

    created = await service.create(
        user_id='user-1',
        payload=PersonaCreate(
            name='Service reviewer',
            description='',
            instructions='Review service-backed work.',
            linked_service_selection=PersonaLinkedServiceSelection(
                linked_service_id='linked-service-1',
                model_id='service-model',
            ),
        ),
    )
    described = await service.describe(user_id='user-1', persona_id=created.id)

    assert described.linked_service_selection == PersonaLinkedServiceSelection(
        linked_service_id='linked-service-1',
        model_id='service-model',
    )
    assert validator.calls == [('workspace-1', 'linked-service-1', 'service-model')]


@pytest.mark.asyncio
async def test_persona_service_requires_linked_service_selection(
    persona_definition_service: PersonaDefinitionService,
    skill_definition_service: SkillDefinitionService,
) -> None:
    """A custom Persona cannot omit its execution connection."""

    service = build_persona_service(
        persona_definition_service,
        skill_definition_service,
    )

    with pytest.raises(ValueError, match='linked-service selection is required'):
        await service.create(
            user_id='user-1',
            payload=PersonaCreate(
                name='Missing service reviewer',
                description='',
                instructions='Review the service association.',
            ),
        )
