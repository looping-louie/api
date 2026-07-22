import pytest

from src.app.services.shared.instruction_service import (
    InstructionCreate,
    InstructionNotFoundError,
    InstructionService,
    InstructionUpdate,
)
from src.app.services.shared.reference_resolver import ResourceReference
from src.app.services.shared.validation_service import (
    DuplicateResourceError,
    ResourceVersionConflictError,
)
from tests.fakes.dependency_checker import (
    FakeDependencyChecker,
    FakeResourceInUseError,
)


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

    assert described == created

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
