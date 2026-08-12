from typing import Sequence

from src.app.services.shared.tenant import WorkspaceMembership


class FakeTenantRepository:
    """In-memory workspace membership repository."""

    def __init__(
        self,
        memberships: Sequence[WorkspaceMembership] | None = None,
    ) -> None:
        self._memberships = list(memberships or [])

    def add(self, membership: WorkspaceMembership) -> None:
        """Add a membership to the repository."""

        self._memberships.append(membership)

    async def get_membership(
        self,
        *,
        user_id: str,
        workspace_id: str,
    ) -> WorkspaceMembership | None:
        for membership in self._memberships:
            if (
                membership.user_id == user_id
                and membership.workspace_id == workspace_id
            ):
                return membership

        return None

    async def get_default_membership(
        self,
        *,
        user_id: str,
    ) -> WorkspaceMembership | None:
        for membership in self._memberships:
            if membership.user_id == user_id and membership.is_default:
                return membership

        return None

    async def list_memberships(
        self,
        *,
        user_id: str,
    ) -> Sequence[WorkspaceMembership]:
        return [
            membership
            for membership in self._memberships
            if membership.user_id == user_id
        ]
