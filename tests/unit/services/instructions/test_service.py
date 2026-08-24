from datetime import UTC, datetime

import pytest

from src.app.catalogs.persona_skills import InstructionOrigin
from src.app.services.instructions import (
    AvailableInstructionDocument,
    BuiltinInstructionImmutableError,
    InstructionCreate,
    InstructionDisabledError,
    InstructionNotFoundError,
    InstructionNotOwnedError,
    InstructionService,
    InstructionType,
    InstructionUpdate,
)
from src.app.services.shared.reference_resolver import ResourceReference
from src.app.services.shared.validation import (
    DuplicateResourceError,
    ResourceVersionConflictError,
)
from tests.fakes.dependency_checker import (
    FakeDependencyChecker,
    FakeResourceInUseError,
)
from tests.fakes.instruction_repository import (
    FakeInstructionRepository,
)


def seed_builtin(
    repository: FakeInstructionRepository,
    *,
    instruction_type: InstructionType,
) -> AvailableInstructionDocument:
    now = datetime(
        2026,
        7,
        23,
        12,
        0,
        tzinfo=UTC,
    )
    document = AvailableInstructionDocument(
        id=f"builtin:{instruction_type}:security",
        workspace_id="catalog",
        instruction_type=instruction_type,
        origin=InstructionOrigin.BUILTIN,
        owner_workspace_id=None,
        source_instruction_id=None,
        name="Security",
        description="Builtin security definition.",
        instructions="Review security.",
        metadata={
            "applies_when": ["security"],
        },
        enabled=True,
        enabled_by_default=True,
        deprecated=False,
        catalog_version=1,
        checksum="a" * 64,
        version=1,
        created_at=now,
        updated_at=now,
    )
    repository.seed_available(document)
    return document


@pytest.mark.asyncio
async def test_create_describe_and_list_instruction(
    instruction_service: InstructionService,
) -> None:
    created = await instruction_service.create(
        workspace_id="workspace-1",
        instruction_type="persona",
        payload=InstructionCreate(
            name="  Tech Lead  ",
            description="  Reviews architecture  ",
            instructions="  Review the proposed architecture.  ",
            metadata={"category": "engineering"},
        ),
    )

    assert created.id == "instruction-1"
    assert created.name == "Tech Lead"
    assert created.description == "Reviews architecture"
    assert created.instructions == "Review the proposed architecture."
    assert created.version == 1
    assert created.metadata == {"category": "engineering"}

    described = await instruction_service.describe(
        workspace_id="workspace-1",
        instruction_type="persona",
        instruction_id=created.id,
    )

    assert described.id == created.id
    assert described.origin == InstructionOrigin.CUSTOM
    assert described.owner_workspace_id == "workspace-1"
    assert described.instructions == created.instructions
    assert described.metadata == created.metadata

    summaries = await instruction_service.list(
        workspace_id="workspace-1",
        instruction_type="persona",
    )

    assert len(summaries) == 1
    assert summaries[0].id == created.id
    assert summaries[0].name == "Tech Lead"


@pytest.mark.asyncio
async def test_list_filters_by_workspace_type_and_search(
    instruction_service: InstructionService,
) -> None:
    await instruction_service.create(
        workspace_id="workspace-1",
        instruction_type="persona",
        payload=InstructionCreate(
            name="Product Manager",
            description="Product strategy",
            instructions="Review the product proposal.",
        ),
    )
    await instruction_service.create(
        workspace_id="workspace-1",
        instruction_type="skill",
        payload=InstructionCreate(
            name="Security",
            description="Security review",
            instructions="Review security risks.",
        ),
    )
    await instruction_service.create(
        workspace_id="workspace-2",
        instruction_type="persona",
        payload=InstructionCreate(
            name="Other Product Manager",
            description="Other workspace",
            instructions="Review another product.",
        ),
    )

    summaries = await instruction_service.list(
        workspace_id="workspace-1",
        instruction_type="persona",
        search="product",
    )

    assert [summary.name for summary in summaries] == ["Product Manager"]


@pytest.mark.asyncio
async def test_create_rejects_duplicate_name(
    instruction_service: InstructionService,
) -> None:
    payload = InstructionCreate(
        name="Security Reviewer",
        description="Security review",
        instructions="Review security.",
    )

    await instruction_service.create(
        workspace_id="workspace-1",
        instruction_type="persona",
        payload=payload,
    )

    with pytest.raises(DuplicateResourceError):
        await instruction_service.create(
            workspace_id="workspace-1",
            instruction_type="persona",
            payload=InstructionCreate(
                name=" security reviewer ",
                description="Duplicate",
                instructions="Duplicate instructions.",
            ),
        )


@pytest.mark.asyncio
async def test_update_changes_fields_and_increments_version(
    instruction_service: InstructionService,
) -> None:
    created = await instruction_service.create(
        workspace_id="workspace-1",
        instruction_type="skill",
        payload=InstructionCreate(
            name="Security",
            description="Initial description",
            instructions="Initial instructions.",
            metadata={"applies_when": ["backend"]},
        ),
    )

    updated = await instruction_service.update(
        workspace_id="workspace-1",
        instruction_type="skill",
        instruction_id=created.id,
        payload=InstructionUpdate(
            expected_version=1,
            description="Updated description",
            metadata={"applies_when": ["backend", "api"]},
        ),
    )

    assert updated.name == "Security"
    assert updated.description == "Updated description"
    assert updated.instructions == "Initial instructions."
    assert updated.metadata == {
        "applies_when": ["backend", "api"],
    }
    assert updated.version == 2
    assert updated.updated_at > updated.created_at


@pytest.mark.asyncio
async def test_update_rejects_stale_version(
    instruction_service: InstructionService,
) -> None:
    created = await instruction_service.create(
        workspace_id="workspace-1",
        instruction_type="persona",
        payload=InstructionCreate(
            name="Architect",
            description="Architecture",
            instructions="Review architecture.",
        ),
    )

    await instruction_service.update(
        workspace_id="workspace-1",
        instruction_type="persona",
        instruction_id=created.id,
        payload=InstructionUpdate(
            expected_version=1,
            description="Updated",
        ),
    )

    with pytest.raises(ResourceVersionConflictError):
        await instruction_service.update(
            workspace_id="workspace-1",
            instruction_type="persona",
            instruction_id=created.id,
            payload=InstructionUpdate(
                expected_version=1,
                description="Stale update",
            ),
        )


@pytest.mark.asyncio
async def test_delete_rejects_blocking_dependency(
    instruction_service: InstructionService,
    dependency_checker: FakeDependencyChecker,
) -> None:
    created = await instruction_service.create(
        workspace_id="workspace-1",
        instruction_type="persona",
        payload=InstructionCreate(
            name="Reviewer",
            description="Review persona",
            instructions="Review the output.",
        ),
    )

    dependency_checker.block(
        workspace_id="workspace-1",
        target=ResourceReference(
            resource_type="persona",
            resource_id=created.id,
        ),
    )

    with pytest.raises(FakeResourceInUseError):
        await instruction_service.delete(
            workspace_id="workspace-1",
            instruction_type="persona",
            instruction_id=created.id,
        )

    described = await instruction_service.describe(
        workspace_id="workspace-1",
        instruction_type="persona",
        instruction_id=created.id,
    )
    assert described.id == created.id


@pytest.mark.asyncio
async def test_delete_removes_instruction(
    instruction_service: InstructionService,
) -> None:
    created = await instruction_service.create(
        workspace_id="workspace-1",
        instruction_type="skill",
        payload=InstructionCreate(
            name="Accessibility",
            description="Accessibility review",
            instructions="Review accessibility.",
        ),
    )

    await instruction_service.delete(
        workspace_id="workspace-1",
        instruction_type="skill",
        instruction_id=created.id,
    )

    with pytest.raises(InstructionNotFoundError):
        await instruction_service.describe(
            workspace_id="workspace-1",
            instruction_type="skill",
            instruction_id=created.id,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "instruction_type",
    [
        "skill",
        "persona",
    ],
)
async def test_builtin_cannot_be_updated_or_deleted(
    instruction_service: InstructionService,
    instruction_repository: FakeInstructionRepository,
    instruction_type: InstructionType,
) -> None:
    builtin = seed_builtin(
        instruction_repository,
        instruction_type=instruction_type,
    )

    with pytest.raises(BuiltinInstructionImmutableError):
        await instruction_service.update(
            workspace_id="workspace-1",
            instruction_type=instruction_type,
            instruction_id=builtin.id,
            payload=InstructionUpdate(
                expected_version=1,
                description="Forbidden",
            ),
        )

    with pytest.raises(BuiltinInstructionImmutableError):
        await instruction_service.delete(
            workspace_id="workspace-1",
            instruction_type=instruction_type,
            instruction_id=builtin.id,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "instruction_type",
    [
        "skill",
        "persona",
    ],
)
async def test_builtin_can_be_disabled_enabled_and_described(
    instruction_service: InstructionService,
    instruction_repository: FakeInstructionRepository,
    instruction_type: InstructionType,
) -> None:
    builtin = seed_builtin(
        instruction_repository,
        instruction_type=instruction_type,
    )
    library = await instruction_service.list(
        workspace_id="workspace-1",
        instruction_type=instruction_type,
    )

    assert builtin.id in {
        instruction.id
        for instruction in library
    }

    disabled = await instruction_service.disable(
        workspace_id="workspace-1",
        instruction_type=instruction_type,
        instruction_id=builtin.id,
    )
    described = await instruction_service.describe(
        workspace_id="workspace-1",
        instruction_type=instruction_type,
        instruction_id=builtin.id,
    )

    assert disabled.enabled is False
    assert described.enabled is False

    with pytest.raises(InstructionDisabledError):
        await instruction_service.resolve_for_selection(
            workspace_id="workspace-1",
            instruction_type=instruction_type,
            instruction_id=builtin.id,
        )

    enabled = await instruction_service.enable(
        workspace_id="workspace-1",
        instruction_type=instruction_type,
        instruction_id=builtin.id,
    )
    selected = await instruction_service.resolve_for_selection(
        workspace_id="workspace-1",
        instruction_type=instruction_type,
        instruction_id=builtin.id,
    )

    assert enabled.enabled is True
    assert selected.id == builtin.id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "instruction_type",
    [
        "skill",
        "persona",
    ],
)
async def test_duplicate_creates_editable_custom_copy(
    instruction_service: InstructionService,
    instruction_repository: FakeInstructionRepository,
    instruction_type: InstructionType,
) -> None:
    builtin = seed_builtin(
        instruction_repository,
        instruction_type=instruction_type,
    )

    duplicate = await instruction_service.duplicate(
        workspace_id="workspace-1",
        instruction_type=instruction_type,
        instruction_id=builtin.id,
    )

    assert duplicate.id != builtin.id
    assert duplicate.workspace_id == "workspace-1"
    assert duplicate.source_instruction_id == builtin.id
    assert duplicate.name == "Security Copy"
    assert duplicate.instructions == builtin.instructions
    assert duplicate.metadata == builtin.metadata

    updated = await instruction_service.update(
        workspace_id="workspace-1",
        instruction_type=instruction_type,
        instruction_id=duplicate.id,
        payload=InstructionUpdate(
            expected_version=1,
            description="Editable fork.",
        ),
    )
    available_copy = await instruction_service.describe(
        workspace_id="workspace-1",
        instruction_type=instruction_type,
        instruction_id=duplicate.id,
    )

    assert updated.version == 2
    assert updated.description == "Editable fork."
    assert available_copy.origin == InstructionOrigin.CUSTOM
    assert available_copy.source_instruction_id == builtin.id


@pytest.mark.asyncio
async def test_mutation_does_not_disclose_foreign_custom(
    instruction_service: InstructionService,
) -> None:
    foreign = await instruction_service.create(
        workspace_id="workspace-2",
        instruction_type="skill",
        payload=InstructionCreate(
            name="Foreign",
            description="Other workspace.",
            instructions="Private instructions.",
        ),
    )

    with pytest.raises(InstructionNotOwnedError):
        await instruction_service.update(
            workspace_id="workspace-1",
            instruction_type="skill",
            instruction_id=foreign.id,
            payload=InstructionUpdate(
                expected_version=1,
                description="Forbidden",
            ),
        )

    with pytest.raises(InstructionNotOwnedError):
        await instruction_service.delete(
            workspace_id="workspace-1",
            instruction_type="skill",
            instruction_id=foreign.id,
        )
