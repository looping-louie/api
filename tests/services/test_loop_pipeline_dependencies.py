"""Regression tests for loop deletion while pipelines reference it."""

from __future__ import annotations

import pytest

from src.app.services.shared.dependency_checker import DependencyUsage
from src.app.services.shared.reference_resolver import ResourceReference
from src.app.services.shared.reference_resolver import ReferenceResolver
from src.app.services.shared.tenant_service import TenantService
from tests.fakes.dependency_checker import (
    FakeDependencyChecker,
    FakeResourceInUseError,
)
from tests.fakes.loop_repository import FakeLoopRepository
from tests.fakes.reference_repository import FakeReferenceRepository
from tests.services.test_loop_service import (
    build_service,
    payload,
    seed_references,
)


@pytest.mark.asyncio
async def test_pipeline_reference_blocks_loop_deletion(
    tenant_service: TenantService,
    reference_repository: FakeReferenceRepository,
    reference_resolver: ReferenceResolver,
) -> None:
    """A pipeline dependency prevents physical deletion of its loop."""

    seed_references(reference_repository)
    repository = FakeLoopRepository()
    dependencies = FakeDependencyChecker()
    service = build_service(
        repository=repository,
        tenant_service=tenant_service,
        reference_resolver=reference_resolver,
        dependency_checker=dependencies,
    )
    created = await service.create(user_id="user-1", payload=payload())
    dependencies.add_usage(
        workspace_id="workspace-1",
        target=ResourceReference("loop", created.id),
        usage=DependencyUsage(
            source=ResourceReference("pipeline", "pipeline-1"),
            relation="loop",
        ),
    )

    with pytest.raises(FakeResourceInUseError):
        await service.delete(user_id="user-1", loop_id=created.id)

    assert await repository.get(
        workspace_id="workspace-1",
        loop_id=created.id,
    ) == created
