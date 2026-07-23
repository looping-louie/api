import pytest

from src.app.services.shared.instruction_service import (
    InstructionDisabledError,
    InstructionCreate,
    InstructionService,
    InstructionUpdate,
)
from src.app.services.shared.tenant_service import (
    TenantService,
    WorkspaceMembership,
)
from src.app.services.skill_service import (
    SkillService,
    SkillValidationError,
)
from tests.fakes.tenant_repository import FakeTenantRepository
from tests.fakes.instruction_repository import (
    FakeInstructionRepository,
)
from tests.services.test_instruction_service import seed_builtin


def build_skill_service(
    instruction_service: InstructionService,
) -> SkillService:
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
async def test_skill_service_exposes_enable_and_duplicate(
    instruction_service: InstructionService,
    instruction_repository: FakeInstructionRepository,
) -> None:
    service = build_skill_service(instruction_service)
    builtin = seed_builtin(
        instruction_repository,
        instruction_type="skill",
    )

    await service.disable(
        user_id="user-1",
        skill_id=builtin.id,
    )

    with pytest.raises(InstructionDisabledError):
        await service.resolve_for_selection(
            user_id="user-1",
            skill_id=builtin.id,
        )

    await service.enable(
        user_id="user-1",
        skill_id=builtin.id,
    )
    duplicate = await service.duplicate(
        user_id="user-1",
        skill_id=builtin.id,
        name="Workspace Security",
    )

    assert duplicate.source_instruction_id == builtin.id
    assert duplicate.name == "Workspace Security"
