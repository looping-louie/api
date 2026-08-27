"""Workspace tenant resolution and membership operations."""

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True, slots=True)
class ProjectContext:
    """Workspace context resolved for the authenticated user."""

    project_id: str
    user_id: str


@dataclass(frozen=True, slots=True)
class ProjectMembership:
    """Relationship between a user and an accessible workspace."""

    user_id: str
    workspace_id: str
    is_enabled: bool = True
    is_default: bool = False


class TenantRepository(Protocol):
    """Persistence contract required by TenantService."""

    async def get_membership(
        self,
        *,
        user_id: str,
        workspace_id: str,
    ) -> ProjectMembership | None:
        """Return the membership between a user and a workspace."""
        ...

    async def get_default_membership(
        self,
        *,
        user_id: str,
    ) -> ProjectMembership | None:
        """Return the user's default workspace membership."""
        ...

    async def list_memberships(
        self,
        *,
        user_id: str,
    ) -> Sequence[ProjectMembership]:
        """Return all workspace memberships belonging to the user."""
        ...


class TenantServiceError(Exception):
    """Base error raised by TenantService."""


class TenantValidationError(TenantServiceError):
    """Raised when tenant resolution receives invalid input."""

    def __init__(self, *, field_name: str, message: str) -> None:
        super().__init__(f"Invalid '{field_name}': {message}")
        self.field_name = field_name
        self.message = message


class TenantNotFoundError(TenantServiceError):
    """Raised when the User has no accessible Project."""

    def __init__(self, *, user_id: str) -> None:
        super().__init__(f"User '{user_id}' has no accessible Project.")
        self.user_id = user_id


class TenantAccessDeniedError(TenantServiceError):
    """Raised when the User cannot access a requested Project."""

    def __init__(self, *, user_id: str, workspace_id: str) -> None:
        message = f"User '{user_id}' does not have access to Project '{workspace_id}'."
        super().__init__(message)
        self.user_id = user_id
        self.workspace_id = workspace_id


class TenantSelectionRequiredError(TenantServiceError):
    """Raised when several Projects exist and none is selected."""

    def __init__(
        self,
        *,
        user_id: str,
        project_ids: Sequence[str],
    ) -> None:
        message = (
            f"User '{user_id}' belongs to multiple Projects and must select "
            "one explicitly."
        )
        super().__init__(message)
        self.user_id = user_id
        self.project_ids = tuple(project_ids)


class TenantService:
    """Resolves and verifies the workspace for an authenticated user."""

    def __init__(self, *, repository: TenantRepository) -> None:
        self._repository = repository

    async def resolve(
        self,
        *,
        user_id: str,
        requested_project_id: str | None = None,
    ) -> ProjectContext:
        """
        Resolve the Project under which an operation must run.

        A requested Project takes precedence. Otherwise, the User's default
        Project is used. When the User only belongs to one enabled Project,
        that Project is selected automatically.
        """

        user_id = self._require_text(user_id, "user_id")
        requested_project_id = self._normalize_optional_text(
            requested_project_id,
        )

        if requested_project_id is not None:
            return await self._resolve_requested_workspace(
                user_id=user_id,
                workspace_id=requested_project_id,
            )

        default_membership = await self._repository.get_default_membership(
            user_id=user_id,
        )

        if default_membership is not None and default_membership.is_enabled:
            return self._build_context(default_membership)

        memberships = await self._repository.list_memberships(user_id=user_id)
        enabled_memberships = [
            membership
            for membership in memberships
            if membership.is_enabled
        ]

        if not enabled_memberships:
            raise TenantNotFoundError(user_id=user_id)

        if len(enabled_memberships) > 1:
            raise TenantSelectionRequiredError(
                user_id=user_id,
                project_ids=[
                    membership.workspace_id
                    for membership in enabled_memberships
                ],
            )

        return self._build_context(enabled_memberships[0])

    async def require_access(
        self,
        *,
        user_id: str,
        workspace_id: str,
    ) -> ProjectContext:
        """Verify access to an explicitly selected Project."""

        return await self.resolve(
            user_id=user_id,
            requested_project_id=workspace_id,
        )

    async def _resolve_requested_workspace(
        self,
        *,
        user_id: str,
        workspace_id: str,
    ) -> ProjectContext:
        membership = await self._repository.get_membership(
            user_id=user_id,
            workspace_id=workspace_id,
        )

        if membership is None or not membership.is_enabled:
            raise TenantAccessDeniedError(
                user_id=user_id,
                workspace_id=workspace_id,
            )

        return self._build_context(membership)

    @staticmethod
    def _build_context(membership: ProjectMembership) -> ProjectContext:
        return ProjectContext(
            project_id=membership.workspace_id,
            user_id=membership.user_id,
        )

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise TenantValidationError(
                field_name=field_name,
                message="must not be empty",
            )

        return normalized

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None
