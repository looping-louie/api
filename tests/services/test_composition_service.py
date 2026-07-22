import pytest

from src.app.services.shared.composition_service import (
    CompositionCreate,
    CompositionNotFoundError,
    CompositionService,
    CompositionUpdate,
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
async def test_create_describe_and_list_composition(
    composition_service: CompositionService,
) -> None:
    created = await composition_service.create(
        workspace_id="workspace-1",
        composition_type="council",
        payload=CompositionCreate(
            name="  Engineering Council ",
            description="  Reviews technical work  ",
            items=[
                {
                    "role": "reviewer",
                    "persona_id": "persona-1",
                    "skill_ids": ["skill-1"],
                },
            ],
        ),
    )

    assert created.id == "composition-1"
    assert created.name == "Engineering Council"
    assert created.description == "Reviews technical work"
    assert created.version == 1
    assert len(created.items) == 1

    described = await composition_service.describe(
        workspace_id="workspace-1",
        composition_type="council",
        composition_id=created.id,
    )

    assert described == created

    summaries = await composition_service.list(
        workspace_id="workspace-1",
        composition_type="council",
    )

    assert len(summaries) == 1
    assert summaries[0].item_count == 1


@pytest.mark.asyncio
async def test_create_rejects_duplicate_composition_name(
    composition_service: CompositionService,
) -> None:
    await composition_service.create(
        workspace_id="workspace-1",
        composition_type="loop",
        payload=CompositionCreate(
            name="Production Loop",
            description="First loop",
        ),
    )

    with pytest.raises(DuplicateResourceError):
        await composition_service.create(
            workspace_id="workspace-1",
            composition_type="loop",
            payload=CompositionCreate(
                name=" production loop ",
                description="Duplicate",
            ),
        )


@pytest.mark.asyncio
async def test_update_preserves_omitted_values(
    composition_service: CompositionService,
) -> None:
    created = await composition_service.create(
        workspace_id="workspace-1",
        composition_type="loop",
        payload=CompositionCreate(
            name="Code Loop",
            description="Initial description",
            attributes={
                "council_id": "council-1",
                "max_iterations": 3,
            },
            items=[
                {
                    "role": "generator",
                    "model_id": "model-1",
                },
            ],
        ),
    )

    updated = await composition_service.update(
        workspace_id="workspace-1",
        composition_type="loop",
        composition_id=created.id,
        payload=CompositionUpdate(
            expected_version=1,
            description="Updated description",
        ),
    )

    assert updated.name == "Code Loop"
    assert updated.description == "Updated description"
    assert updated.attributes == {
        "council_id": "council-1",
        "max_iterations": 3,
    }
    assert updated.items == (
        {
            "role": "generator",
            "model_id": "model-1",
        },
    )
    assert updated.version == 2


@pytest.mark.asyncio
async def test_update_rejects_stale_version(
    composition_service: CompositionService,
) -> None:
    created = await composition_service.create(
        workspace_id="workspace-1",
        composition_type="council",
        payload=CompositionCreate(
            name="Council",
            description="Description",
        ),
    )

    await composition_service.update(
        workspace_id="workspace-1",
        composition_type="council",
        composition_id=created.id,
        payload=CompositionUpdate(
            expected_version=1,
            description="Updated",
        ),
    )

    with pytest.raises(ResourceVersionConflictError):
        await composition_service.update(
            workspace_id="workspace-1",
            composition_type="council",
            composition_id=created.id,
            payload=CompositionUpdate(
                expected_version=1,
                description="Stale update",
            ),
        )


@pytest.mark.asyncio
async def test_delete_rejects_blocking_dependency(
    composition_service: CompositionService,
    dependency_checker: FakeDependencyChecker,
) -> None:
    created = await composition_service.create(
        workspace_id="workspace-1",
        composition_type="council",
        payload=CompositionCreate(
            name="Council",
            description="Description",
        ),
    )

    dependency_checker.block(
        workspace_id="workspace-1",
        target=ResourceReference(
            resource_type="council",
            resource_id=created.id,
        ),
        source_type="loop",
        source_id="loop-1",
        relation="council",
    )

    with pytest.raises(FakeResourceInUseError):
        await composition_service.delete(
            workspace_id="workspace-1",
            composition_type="council",
            composition_id=created.id,
        )


@pytest.mark.asyncio
async def test_delete_removes_composition(
    composition_service: CompositionService,
) -> None:
    created = await composition_service.create(
        workspace_id="workspace-1",
        composition_type="loop",
        payload=CompositionCreate(
            name="Temporary Loop",
            description="Temporary",
        ),
    )

    await composition_service.delete(
        workspace_id="workspace-1",
        composition_type="loop",
        composition_id=created.id,
    )

    with pytest.raises(CompositionNotFoundError):
        await composition_service.describe(
            workspace_id="workspace-1",
            composition_type="loop",
            composition_id=created.id,
        )
