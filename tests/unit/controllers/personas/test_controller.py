"""Tests for persona instruction controllers."""

import pytest

from src.app.catalogs.persona_skills import InstructionOrigin
from src.app.controllers.persona import PersonaController
from src.app.schemas.persona import PersonaCreateRequest, PersonaPatchRequest
from src.app.services.persona_skills import (
    PersonaDefinitionService,
    SkillDefinitionService,
)
from src.app.services.personas import PersonaService
from tests.fakes.instruction_repository import FakeInstructionRepository
from tests.unit.services.instructions.test_service import seed_builtin
from tests.unit.services.personas.test_service import build_persona_service


@pytest.mark.asyncio
async def test_persona_controller_patches_and_creates(
    persona_definition_service: PersonaDefinitionService,
    skill_definition_service: SkillDefinitionService,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """Persona controller patches enablement and creates content."""
    service: PersonaService = build_persona_service(
        persona_definition_service,
        skill_definition_service,
    )
    controller = PersonaController(persona_service=service)
    builtin = seed_builtin(
        instruction_repository,
        instruction_type='persona',
    )

    disabled = await controller.patch(
        user_id='user-1',
        persona_id=builtin.id,
        payload=PersonaPatchRequest(enabled=False),
    )
    copied = await controller.create(
        user_id='user-1',
        payload=PersonaCreateRequest(
            name='Workspace_Lead',
            instructions='Lead workspace reviews.',
            linked_service={
                'type': 'LinkedServiceReference',
                'reference_id': 'linked-service-1',
            },
            config={'model': 'service-model'},
        ),
    )

    assert disabled.origin == InstructionOrigin.BUILTIN
    assert disabled.enabled is False
    assert disabled.editable is False
    assert copied.origin == InstructionOrigin.CUSTOM
    assert copied.enabled is True
    assert copied.editable is True
    assert copied.duplicable is True
    assert copied.source_instruction_id is None
    assert 'owner_workspace_id' not in copied.model_dump()
