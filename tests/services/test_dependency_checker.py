import pytest

from src.app.services.shared.dependency_checker import (
    DependencyChecker,
    DependencyUsage,
    ResourceInUseError,
)
from src.app.services.shared.reference_resolver import ResourceReference
from tests.fakes.dependency_repository import FakeDependencyRepository


@pytest.mark.asyncio
async def test_find_usages_normalizes_and_removes_duplicates(
    dependency_repository: FakeDependencyRepository,
) -> None:
    target = ResourceReference("persona", "persona-1")
    usage = DependencyUsage(
        source=ResourceReference("COUNCIL", "council-1"),
        relation=" assignment ",
        blocking=True,
    )
    dependency_repository.add_usage(
        workspace_id="workspace-1",
        target=target,
        usage=usage,
    )
    dependency_repository.add_usage(
        workspace_id="workspace-1",
        target=target,
        usage=usage,
    )

    checker = DependencyChecker(
        repository=dependency_repository,
    )
    usages = await checker.find_usages(
        workspace_id="workspace-1",
        target=target,
    )

    assert usages == [
        DependencyUsage(
            source=ResourceReference("council", "council-1"),
            relation="assignment",
            blocking=True,
        )
    ]


@pytest.mark.asyncio
async def test_non_blocking_usage_allows_deletion(
    dependency_repository: FakeDependencyRepository,
) -> None:
    target = ResourceReference("loop", "loop-1")
    dependency_repository.add_usage(
        workspace_id="workspace-1",
        target=target,
        usage=DependencyUsage(
            source=ResourceReference("run", "run-1"),
            relation="snapshot",
            blocking=False,
        ),
    )

    checker = DependencyChecker(
        repository=dependency_repository,
    )

    await checker.require_deletable(
        workspace_id="workspace-1",
        target=target,
    )

    assert not await checker.has_blocking_usages(
        workspace_id="workspace-1",
        target=target,
    )


@pytest.mark.asyncio
async def test_blocking_usage_prevents_deletion(
    dependency_repository: FakeDependencyRepository,
) -> None:
    target = ResourceReference("council", "council-1")
    dependency_repository.add_usage(
        workspace_id="workspace-1",
        target=target,
        usage=DependencyUsage(
            source=ResourceReference("loop", "loop-1"),
            relation="council",
            blocking=True,
        ),
    )

    checker = DependencyChecker(
        repository=dependency_repository,
    )

    with pytest.raises(ResourceInUseError) as error:
        await checker.require_deletable(
            workspace_id="workspace-1",
            target=target,
        )

    assert error.value.target == target
    assert error.value.usages == (
        DependencyUsage(
            source=ResourceReference("loop", "loop-1"),
            relation="council",
            blocking=True,
        ),
    )
