"""Tests for persona and skill instruction controllers."""

import pytest

from src.app.catalogs.instructions import InstructionOrigin
from src.app.controllers.persona import PersonaController
from src.app.controllers.skill import SkillController
from src.app.schemas.persona import (
    PersonaCreateRequest,
    PersonaPatchRequest,
)
from src.app.schemas.skill import (
    SkillCreateRequest,
    SkillPatchRequest,
)
from src.app.services.persona_service import PersonaService
from src.app.services.shared.instruction_service import InstructionService
from src.app.services.skill_service import SkillService
from tests.fakes.instruction_repository import FakeInstructionRepository
from tests.services.test_instruction_service import seed_builtin
from tests.services.test_persona_service import build_persona_service
from tests.services.test_skill_service import build_skill_service


@pytest.mark.asyncio
async def test_skill_controller_patches_and_creates_from_source(
    instruction_service: InstructionService,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """Skill controller patches enablement and creates sourced copies."""

    service: SkillService = build_skill_service(instruction_service)
    controller = SkillController(skill_service=service)
    builtin = seed_builtin(
        instruction_repository,
        instruction_type="skill",
    )

    listed = await controller.list(user_id="user-1")
    disabled = await controller.patch(
        user_id="user-1",
        skill_id=builtin.id,
        payload=SkillPatchRequest(enabled=False),
    )
    copied = await controller.create(
        user_id="user-1",
        payload=SkillCreateRequest(
            source_skill_id=builtin.id,
            name="Workspace Security",
        ),
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
    assert copied.origin == InstructionOrigin.CUSTOM
    assert copied.editable is True
    assert copied.source_instruction_id == builtin.id
    assert "owner_workspace_id" not in copied.model_dump()
    assert "workspace_id" not in copied.model_dump()


@pytest.mark.asyncio
async def test_persona_controller_patches_and_creates_from_source(
    instruction_service: InstructionService,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """Persona controller patches enablement and creates sourced copies."""

    service: PersonaService = build_persona_service(instruction_service)
    controller = PersonaController(persona_service=service)
    builtin = seed_builtin(
        instruction_repository,
        instruction_type="persona",
    )

    disabled = await controller.patch(
        user_id="user-1",
        persona_id=builtin.id,
        payload=PersonaPatchRequest(enabled=False),
    )
    copied = await controller.create(
        user_id="user-1",
        payload=PersonaCreateRequest(
            source_persona_id=builtin.id,
            name="Workspace Lead",
        ),
    )

    assert disabled.origin == InstructionOrigin.BUILTIN
    assert disabled.enabled is False
    assert disabled.editable is False
    assert copied.origin == InstructionOrigin.CUSTOM
    assert copied.enabled is True
    assert copied.editable is True
    assert copied.duplicable is True
    assert copied.source_instruction_id == builtin.id
    assert "owner_workspace_id" not in copied.model_dump()
