"""Tests for workspace-aware skill operations."""

import pytest

from src.app.services.persona_skills import (
    DefinitionCreate,
    DefinitionUpdate,
    SkillDefinitionService,
)
from src.app.services.skills import SkillService, SkillValidationError
from tests.fakes.instruction_repository import (
    FakeInstructionRepository,
)
from tests.unit.services.instructions.test_service import seed_builtin


def build_skill_service(
    skill_definition_service: SkillDefinitionService,
) -> SkillService:
    """Build a Skill service with a registered user profile."""

    return SkillService(
        user_service=RegisteredUserService(),
        skill_definition_service=skill_definition_service,
    )


class RegisteredUserService:
    """Minimal user-profile boundary for user-owned Skill tests."""

    async def get(self, *, user_id: str) -> object:
        """Accept the registered test identity."""

        assert user_id == 'user-1'
        return object()


@pytest.mark.asyncio
async def test_create_skill_with_valid_metadata(
    skill_definition_service: SkillDefinitionService,
) -> None:
    """Valid structured metadata is preserved on skill creation."""

    service = build_skill_service(skill_definition_service)

    created = await service.create(
        user_id="user-1",
        payload=DefinitionCreate(
            name="Security",
            description="Reviews security risks",
            instructions="Review the code for security vulnerabilities.",
            metadata={
                "category": "security_privacy",
                "applies_when": ["backend", "api"],
                "default_strictness": {
                    "prototype": 30,
                    "mvp": 60,
                    "production": 90,
                },
            },
        ),
    )

    assert created.instruction_type == "skill"
    assert created.metadata["category"] == "security_privacy"
    assert created.metadata["applies_when"] == ["backend", "api"]


@pytest.mark.asyncio
async def test_create_skill_rejects_unknown_category(
    skill_definition_service: SkillDefinitionService,
) -> None:
    """Custom skills use the same stable taxonomy as packaged skills."""

    service = build_skill_service(skill_definition_service)

    with pytest.raises(SkillValidationError):
        await service.create(
            user_id="user-1",
            payload=DefinitionCreate(
                name="Unknown area",
                description="Uses an unsupported category.",
                instructions="Review the supplied work.",
                metadata={"category": "miscellaneous"},
            ),
        )


@pytest.mark.asyncio
async def test_create_skill_rejects_duplicate_applies_when(
    skill_definition_service: SkillDefinitionService,
) -> None:
    """Applicability values must be unique without case differences."""

    service = build_skill_service(skill_definition_service)

    with pytest.raises(SkillValidationError):
        await service.create(
            user_id="user-1",
            payload=DefinitionCreate(
                name="Security",
                description="Reviews security",
                instructions="Review security.",
                metadata={
                    "applies_when": ["backend", "BACKEND"],
                },
            ),
        )


@pytest.mark.asyncio
async def test_create_skill_rejects_empty_applies_when(
    skill_definition_service: SkillDefinitionService,
) -> None:
    """Applicability metadata cannot be an empty list."""

    service = build_skill_service(skill_definition_service)

    with pytest.raises(SkillValidationError):
        await service.create(
            user_id="user-1",
            payload=DefinitionCreate(
                name="Security",
                description="Reviews security",
                instructions="Review security.",
                metadata={
                    "applies_when": [],
                },
            ),
        )


@pytest.mark.asyncio
async def test_create_skill_rejects_invalid_strictness(
    skill_definition_service: SkillDefinitionService,
) -> None:
    """Strictness values must stay within the supported range."""

    service = build_skill_service(skill_definition_service)

    with pytest.raises(SkillValidationError):
        await service.create(
            user_id="user-1",
            payload=DefinitionCreate(
                name="Security",
                description="Reviews security",
                instructions="Review security.",
                metadata={
                    "default_strictness": {
                        "production": 120,
                    },
                },
            ),
        )


@pytest.mark.asyncio
async def test_create_skill_rejects_unknown_strictness_phase(
    skill_definition_service: SkillDefinitionService,
) -> None:
    """Strictness metadata rejects unsupported project phases."""

    service = build_skill_service(skill_definition_service)

    with pytest.raises(SkillValidationError):
        await service.create(
            user_id="user-1",
            payload=DefinitionCreate(
                name="Security",
                description="Reviews security",
                instructions="Review security.",
                metadata={
                    "default_strictness": {
                        "enterprise": 90,
                    },
                },
            ),
        )


@pytest.mark.asyncio
async def test_update_skill_without_metadata_preserves_metadata(
    skill_definition_service: SkillDefinitionService,
) -> None:
    """Omitted update metadata preserves the stored metadata."""

    service = build_skill_service(skill_definition_service)

    created = await service.create(
        user_id="user-1",
        payload=DefinitionCreate(
            name="Security",
            description="Initial description",
            instructions="Review security.",
            metadata={
                "applies_when": ["backend"],
            },
        ),
    )

    updated = await service.update(
        user_id="user-1",
        skill_id=created.id,
        payload=DefinitionUpdate(
            expected_version=1,
            description="Updated description",
        ),
    )

    assert updated.description == "Updated description"
    assert updated.metadata == {
        "applies_when": ["backend"],
    }


@pytest.mark.asyncio
async def test_skill_service_sets_enabled_and_creates_content(
    skill_definition_service: SkillDefinitionService,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """Skill-specific methods support PATCH and direct POST workflows."""

    service = build_skill_service(skill_definition_service)
    builtin = seed_builtin(
        instruction_repository,
        instruction_type="skill",
    )

    await service.set_enabled(
        user_id="user-1",
        skill_id=builtin.id,
        enabled=False,
    )

    await service.set_enabled(
        user_id="user-1",
        skill_id=builtin.id,
        enabled=True,
    )
    created = await service.create(
        user_id="user-1",
        payload=DefinitionCreate(
            name="Project Security",
            description=builtin.description,
            instructions=builtin.instructions,
            metadata=builtin.metadata,
        ),
    )

    assert created.source_instruction_id is None
    assert created.name == "Project Security"
    assert created.metadata == builtin.metadata
