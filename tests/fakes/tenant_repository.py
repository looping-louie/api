from typing import Sequence

from src.app.services.shared.tenant import ProjectMembership


class FakeTenantRepository:
    """In-memory workspace membership repository."""

    def __init__(
        self,
        memberships: Sequence[ProjectMembership] | None = None,
    ) -> None:
        self._memberships = list(memberships or [])

    def add(self, membership: ProjectMembership) -> None:
        """Add a membership to the repository."""

        self._memberships.append(membership)

    async def get_membership(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> ProjectMembership | None:
        for membership in self._memberships:
            if (
                membership.user_id == user_id
                and membership.project_id == project_id
            ):
                return membership

        return None

    async def get_default_membership(
        self,
        *,
        user_id: str,
    ) -> ProjectMembership | None:
        for membership in self._memberships:
            if membership.user_id == user_id and membership.is_default:
                return membership

        return None

    async def list_memberships(
        self,
        *,
        user_id: str,
    ) -> Sequence[ProjectMembership]:
        return [
            membership
            for membership in self._memberships
            if membership.user_id == user_id
        ]
