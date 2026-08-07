"""Tests for workspace-aware skill operations."""

import pytest

from src.app.services.shared.instruction import (
    InstructionCreate,
    InstructionService,
    InstructionUpdate,
)
from src.app.services.shared.tenant import (
    TenantService,
    WorkspaceMembership,
)
from src.app.services.skills.metadata_validator import SkillValidationError
from src.app.services.skills.service import SkillService
from tests.fakes.tenant_repository import FakeTenantRepository
from tests.fakes.instruction_repository import (
    FakeInstructionRepository,
)
from tests.services.test_instruction_service import seed_builtin


def build_skill_service(
    instruction_service: InstructionService,
) -> SkillService:
    """Build a skill service with one default workspace membership."""

    repository = FakeTenantRepository(
        [
            WorkspaceMembership(
                user_id="user-1",
                workspace_id="workspace-1",
                is_default=True,
            ),
        ]
    )

    return SkillService(
        tenant_service=TenantService(repository=repository),
        instruction_service=instruction_service,
    )


@pytest.mark.asyncio
async def test_create_skill_with_valid_metadata(
    instruction_service: InstructionService,
) -> None:
    """Valid structured metadata is preserved on skill creation."""

    service = build_skill_service(instruction_service)

    created = await service.create(
        user_id="user-1",
        payload=InstructionCreate(
            name="Security",
            description="Reviews security risks",
            instructions="Review the code for security vulnerabilities.",
            metadata={
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
    assert created.metadata["applies_when"] == ["backend", "api"]


@pytest.mark.asyncio
async def test_create_skill_rejects_duplicate_applies_when(
    instruction_service: InstructionService,
) -> None:
    """Applicability values must be unique without case differences."""

    service = build_skill_service(instruction_service)

    with pytest.raises(SkillValidationError):
        await service.create(
            user_id="user-1",
            payload=InstructionCreate(
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
    instruction_service: InstructionService,
) -> None:
    """Applicability metadata cannot be an empty list."""

    service = build_skill_service(instruction_service)

    with pytest.raises(SkillValidationError):
        await service.create(
            user_id="user-1",
            payload=InstructionCreate(
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
    instruction_service: InstructionService,
) -> None:
    """Strictness values must stay within the supported range."""

    service = build_skill_service(instruction_service)

    with pytest.raises(SkillValidationError):
        await service.create(
            user_id="user-1",
            payload=InstructionCreate(
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
    instruction_service: InstructionService,
) -> None:
    """Strictness metadata rejects unsupported project phases."""

    service = build_skill_service(instruction_service)

    with pytest.raises(SkillValidationError):
        await service.create(
            user_id="user-1",
            payload=InstructionCreate(
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
    instruction_service: InstructionService,
) -> None:
    """Omitted update metadata preserves the stored metadata."""

    service = build_skill_service(instruction_service)

    created = await service.create(
        user_id="user-1",
        payload=InstructionCreate(
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
        payload=InstructionUpdate(
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
    instruction_service: InstructionService,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """Skill-specific methods support PATCH and direct POST workflows."""

    service = build_skill_service(instruction_service)
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
        payload=InstructionCreate(
            name="Workspace Security",
            description=builtin.description,
            instructions=builtin.instructions,
            metadata=builtin.metadata,
        ),
    )

    assert created.source_instruction_id is None
    assert created.name == "Workspace Security"
    assert created.metadata == builtin.metadata
