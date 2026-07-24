"""In-memory reference repository for service tests."""

from copy import deepcopy
from typing import Mapping, Sequence


class FakeReferenceRepository:
    """In-memory repository for resolving cross-resource references."""

    def __init__(self) -> None:
        """Initialize empty resources and a lookup call log."""

        self._resources: dict[tuple[str, str, str], object] = {}
        self.calls: list[tuple[str, str, tuple[str, ...]]] = []

    def seed(
        self,
        *,
        workspace_id: str,
        resource_type: str,
        resource_id: str,
        value: object,
    ) -> None:
        """Register a resource that can later be resolved."""

        key = self._build_key(
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        self._resources[key] = deepcopy(value)

    def remove(
        self,
        *,
        workspace_id: str,
        resource_type: str,
        resource_id: str,
    ) -> None:
        """Remove a resource from the fake repository."""

        key = self._build_key(
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        self._resources.pop(key, None)

    async def get_many(
        self,
        *,
        workspace_id: str,
        resource_type: str,
        resource_ids: Sequence[str],
    ) -> Mapping[str, object]:
        """Return requested resources visible in one workspace."""

        normalized_type = resource_type.casefold()
        requested_ids = tuple(resource_ids)

        self.calls.append(
            (
                workspace_id,
                normalized_type,
                requested_ids,
            )
        )

        resources: dict[str, object] = {}

        for resource_id in requested_ids:
            key = self._build_key(
                workspace_id=workspace_id,
                resource_type=normalized_type,
                resource_id=resource_id,
            )
            value = self._resources.get(key)

            if value is not None:
                resources[resource_id] = deepcopy(value)

        return resources

    @staticmethod
    def _build_key(
        *,
        workspace_id: str,
        resource_type: str,
        resource_id: str,
    ) -> tuple[str, str, str]:
        """Build a normalized in-memory resource key."""

        return workspace_id, resource_type.casefold(), resource_id
