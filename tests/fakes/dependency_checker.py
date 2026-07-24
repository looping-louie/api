"""In-memory dependency checker fake for service tests."""

from dataclasses import dataclass

from src.app.services.shared.dependency_checker import DependencyUsage
from src.app.services.shared.reference_resolver import ResourceReference


@dataclass(frozen=True, slots=True)
class FakeResourceInUseError(Exception):
    """Raised when a fake resource has blocking dependencies."""

    target: ResourceReference
    usages: tuple[DependencyUsage, ...]

    def __str__(self) -> str:
        return (
            f"{self.target.resource_type} '{self.target.resource_id}' "
            "has blocking dependencies."
        )


class FakeDependencyChecker:
    """In-memory dependency checker."""

    def __init__(self) -> None:
        self._usages: dict[
            tuple[str, str, str],
            list[DependencyUsage],
        ] = {}

    def add_usage(
        self,
        *,
        workspace_id: str,
        target: ResourceReference,
        usage: DependencyUsage,
    ) -> None:
        key = self._build_key(
            workspace_id=workspace_id,
            target=target,
        )
        self._usages.setdefault(key, []).append(usage)

    def block(
        self,
        *,
        workspace_id: str,
        target: ResourceReference,
        source_type: str = "loop",
        source_id: str = "loop-1",
        relation: str = "assignment",
    ) -> None:
        """Convenience helper for adding one blocking dependency."""

        self.add_usage(
            workspace_id=workspace_id,
            target=target,
            usage=DependencyUsage(
                source=ResourceReference(
                    resource_type=source_type,
                    resource_id=source_id,
                ),
                relation=relation,
                blocking=True,
            ),
        )

    async def find_usages(
        self,
        *,
        workspace_id: str,
        target: ResourceReference,
    ) -> list[DependencyUsage]:
        key = self._build_key(
            workspace_id=workspace_id,
            target=target,
        )
        return list(self._usages.get(key, []))

    async def require_deletable(
        self,
        *,
        workspace_id: str,
        target: ResourceReference,
    ) -> None:
        usages = await self.find_usages(
            workspace_id=workspace_id,
            target=target,
        )
        blocking_usages = tuple(
            usage
            for usage in usages
            if usage.blocking
        )

        if blocking_usages:
            raise FakeResourceInUseError(
                target=target,
                usages=blocking_usages,
            )

    @staticmethod
    def _build_key(
        *,
        workspace_id: str,
        target: ResourceReference,
    ) -> tuple[str, str, str]:
        return (
            workspace_id,
            target.resource_type,
            target.resource_id,
        )
