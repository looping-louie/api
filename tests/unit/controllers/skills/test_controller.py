"""Tests for skill instruction controllers."""

import pytest

from src.app.catalogs.persona_skills import InstructionOrigin
from src.app.controllers.skill import SkillController
from src.app.schemas.skill import SkillCreateRequest, SkillPatchRequest
from src.app.services.persona_skills import SkillDefinitionService
from src.app.services.skills import SkillService
from tests.fakes.instruction_repository import FakeInstructionRepository
from tests.unit.services.instructions.test_service import seed_builtin
from tests.unit.services.skills.test_service import build_skill_service


@pytest.mark.asyncio
async def test_skill_controller_lists_patches_and_creates(
    skill_definition_service: SkillDefinitionService,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """Skill controller lists, patches enablement, and creates content."""
    service: SkillService = build_skill_service(skill_definition_service)
    controller = SkillController(skill_service=service)
    builtin = seed_builtin(
        instruction_repository,
        instruction_type='skill',
    )

    listed = await controller.list(user_id='user-1')
    disabled = await controller.patch(
        user_id='user-1',
        skill_id=builtin.id,
        payload=SkillPatchRequest(enabled=False),
    )
    copied = await controller.create(
        user_id='user-1',
        payload=SkillCreateRequest(
            name='Project Security',
            instructions='Review workspace security.',
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
    assert copied.source_instruction_id is None
    assert 'owner_project_id' not in copied.model_dump()
    assert 'project_id' not in copied.model_dump()
