import pytest

from src.app.services.shared.reference_resolver import (
    ReferenceResolver,
    ResourceNotFoundError,
    ResourceReference,
)
from tests.fakes.reference_repository import FakeReferenceRepository


@pytest.mark.asyncio
async def test_require_one_resolves_resource(
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
) -> None:
    reference_repository.seed(
        workspace_id="workspace-1",
        resource_type="persona",
        resource_id="persona-1",
        value={"name": "Tech Lead"},
    )

    resolved = await reference_resolver.require_one(
        workspace_id="workspace-1",
        reference=ResourceReference(
            resource_type="PERSONA",
            resource_id="persona-1",
        ),
    )

    assert resolved.reference == ResourceReference(
        resource_type="persona",
        resource_id="persona-1",
    )
    assert resolved.value == {"name": "Tech Lead"}


@pytest.mark.asyncio
async def test_require_many_preserves_order_and_duplicates(
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
) -> None:
    reference_repository.seed(
        workspace_id="workspace-1",
        resource_type="skill",
        resource_id="skill-1",
        value={"name": "Security"},
    )
    reference_repository.seed(
        workspace_id="workspace-1",
        resource_type="persona",
        resource_id="persona-1",
        value={"name": "Reviewer"},
    )

    resolved = await reference_resolver.require_many(
        workspace_id="workspace-1",
        references=[
            ResourceReference("skill", "skill-1"),
            ResourceReference("persona", "persona-1"),
            ResourceReference("skill", "skill-1"),
        ],
    )

    assert [
        item.reference
        for item in resolved
    ] == [
        ResourceReference("skill", "skill-1"),
        ResourceReference("persona", "persona-1"),
        ResourceReference("skill", "skill-1"),
    ]

    assert reference_repository.calls == [
        (
            "workspace-1",
            "skill",
            ("skill-1",),
        ),
        (
            "workspace-1",
            "persona",
            ("persona-1",),
        ),
    ]


@pytest.mark.asyncio
async def test_require_many_reports_all_missing_references(
    reference_resolver: ReferenceResolver,
) -> None:
    references = [
        ResourceReference("persona", "persona-missing"),
        ResourceReference("skill", "skill-missing"),
        ResourceReference("persona", "persona-missing"),
    ]

    with pytest.raises(ResourceNotFoundError) as error:
        await reference_resolver.require_many(
            workspace_id="workspace-1",
            references=references,
        )

    assert error.value.references == (
        ResourceReference("persona", "persona-missing"),
        ResourceReference("skill", "skill-missing"),
    )


@pytest.mark.asyncio
async def test_resolver_does_not_cross_workspace_boundaries(
    reference_resolver: ReferenceResolver,
    reference_repository: FakeReferenceRepository,
) -> None:
    reference_repository.seed(
        workspace_id="workspace-2",
        resource_type="persona",
        resource_id="persona-1",
        value={"name": "Other persona"},
    )

    with pytest.raises(ResourceNotFoundError):
        await reference_resolver.require_one(
            workspace_id="workspace-1",
            reference=ResourceReference(
                resource_type="persona",
                resource_id="persona-1",
            ),
        )
