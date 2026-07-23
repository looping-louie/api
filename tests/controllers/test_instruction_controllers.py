import pytest

from src.app.catalogs.instructions import InstructionOrigin
from src.app.controllers.persona import PersonaController
from src.app.controllers.skill import SkillController
from src.app.schemas.persona import (
    PersonaDuplicateRequest,
    PersonaEnabledRequest,
)
from src.app.schemas.skill import (
    SkillDuplicateRequest,
    SkillEnabledRequest,
)
from src.app.services.persona_service import PersonaService
from src.app.services.shared.instruction_service import InstructionService
from src.app.services.skill_service import SkillService
from tests.fakes.instruction_repository import FakeInstructionRepository
from tests.services.test_instruction_service import seed_builtin
from tests.services.test_persona_service import build_persona_service
from tests.services.test_skill_service import build_skill_service


@pytest.mark.asyncio
async def test_skill_controller_exposes_effective_capabilities(
    instruction_service: InstructionService,
    instruction_repository: FakeInstructionRepository,
) -> None:
    service: SkillService = build_skill_service(instruction_service)
    controller = SkillController(skill_service=service)
    builtin = seed_builtin(
        instruction_repository,
        instruction_type="skill",
    )

    listed = await controller.list(user_id="user-1")
    disabled = await controller.set_enabled(
        user_id="user-1",
        skill_id=builtin.id,
        payload=SkillEnabledRequest(enabled=False),
    )
    duplicate = await controller.duplicate(
        user_id="user-1",
        skill_id=builtin.id,
        payload=SkillDuplicateRequest(name="Workspace Security"),
    )

    summary = listed.items[0]
    assert summary.origin == InstructionOrigin.BUILTIN
    assert summary.enabled is True
    assert summary.editable is False
    assert summary.duplicable is True
    assert summary.deprecated is False
    assert summary.catalog_version == 1
    assert summary.source_instruction_id is None
    assert disabled.enabled is False
    assert duplicate.origin == InstructionOrigin.CUSTOM
    assert duplicate.editable is True
    assert duplicate.source_instruction_id == builtin.id
    assert "owner_workspace_id" not in duplicate.model_dump()
    assert "workspace_id" not in duplicate.model_dump()


@pytest.mark.asyncio
async def test_persona_controller_enables_and_duplicates_builtin(
    instruction_service: InstructionService,
    instruction_repository: FakeInstructionRepository,
) -> None:
    service: PersonaService = build_persona_service(instruction_service)
    controller = PersonaController(persona_service=service)
    builtin = seed_builtin(
        instruction_repository,
        instruction_type="persona",
    )

    disabled = await controller.set_enabled(
        user_id="user-1",
        persona_id=builtin.id,
        payload=PersonaEnabledRequest(enabled=False),
    )
    duplicate = await controller.duplicate(
        user_id="user-1",
        persona_id=builtin.id,
        payload=PersonaDuplicateRequest(name="Workspace Lead"),
    )

    assert disabled.origin == InstructionOrigin.BUILTIN
    assert disabled.enabled is False
    assert disabled.editable is False
    assert duplicate.origin == InstructionOrigin.CUSTOM
    assert duplicate.enabled is True
    assert duplicate.editable is True
    assert duplicate.duplicable is True
    assert duplicate.source_instruction_id == builtin.id
    assert "owner_workspace_id" not in duplicate.model_dump()

