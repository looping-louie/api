"""Unit tests for shared dependency checking behavior."""

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
    """Normalize duplicate repository usages into one stable result."""

    target = ResourceReference("persona", "persona-1")
    usage = DependencyUsage(
        source=ResourceReference("LOOP", "loop-1"),
        relation=" persona ",
        blocking=True,
    )
    dependency_repository.add_usage(
        project_id="workspace-1",
        target=target,
        usage=usage,
    )
    dependency_repository.add_usage(
        project_id="workspace-1",
        target=target,
        usage=usage,
    )

    checker = DependencyChecker(
        repository=dependency_repository,
    )
    usages = await checker.find_usages(
        project_id="workspace-1",
        target=target,
    )

    assert usages == [
        DependencyUsage(
            source=ResourceReference("loop", "loop-1"),
            relation="persona",
            blocking=True,
        )
    ]


@pytest.mark.asyncio
async def test_non_blocking_usage_allows_deletion(
    dependency_repository: FakeDependencyRepository,
) -> None:
    """Informational usages do not block resource deletion."""

    target = ResourceReference("loop", "loop-1")
    dependency_repository.add_usage(
        project_id="workspace-1",
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
        project_id="workspace-1",
        target=target,
    )


@pytest.mark.asyncio
async def test_blocking_usage_prevents_deletion(
    dependency_repository: FakeDependencyRepository,
) -> None:
    """Blocking usages raise a detailed resource-in-use error."""

    target = ResourceReference("persona", "persona-1")
    dependency_repository.add_usage(
        project_id="workspace-1",
        target=target,
        usage=DependencyUsage(
            source=ResourceReference("loop", "loop-1"),
            relation="persona",
            blocking=True,
        ),
    )

    checker = DependencyChecker(
        repository=dependency_repository,
    )

    with pytest.raises(ResourceInUseError) as error:
        await checker.require_deletable(
            project_id="workspace-1",
            target=target,
        )

    assert error.value.target == target
    assert error.value.usages == (
        DependencyUsage(
            source=ResourceReference("loop", "loop-1"),
            relation="persona",
            blocking=True,
        ),
    )
