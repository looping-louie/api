from typing import Sequence

from src.app.services.shared.dependency_checker import DependencyUsage
from src.app.services.shared.reference_resolver import ResourceReference


class FakeDependencyRepository:
    """In-memory repository used to test DependencyChecker."""

    def __init__(self) -> None:
        self._usages: dict[
            tuple[str, str, str],
            list[DependencyUsage],
        ] = {}

    def add_usage(
        self,
        *,
        project_id: str,
        target: ResourceReference,
        usage: DependencyUsage,
    ) -> None:
        """Register one dependency usage."""

        key = self._build_key(
            project_id=project_id,
            target=target,
        )
        self._usages.setdefault(key, []).append(usage)

    async def find_usages(
        self,
        *,
        project_id: str,
        target: ResourceReference,
    ) -> Sequence[DependencyUsage]:
        key = self._build_key(
            project_id=project_id,
            target=target,
        )

        return list(self._usages.get(key, []))

    @staticmethod
    def _build_key(
        *,
        project_id: str,
        target: ResourceReference,
    ) -> tuple[str, str, str]:
        return (
            project_id,
            target.resource_type.casefold(),
            target.resource_id,
        )
