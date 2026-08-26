"""Application service for workspaces."""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from src.app.models.workspace import WorkspaceDocument
from src.app.repositories.workspaces import WorkspaceRepository
from src.app.services.linked_services import LinkedServiceService
from src.app.services.shared.tenant import TenantService
from src.app.services.users import UserService


class WorkspaceService:
    """Manage User-owned Workspaces."""

    def __init__(
        self,
        *,
        repository: WorkspaceRepository,
        tenant_service: TenantService,
        linked_service_service: LinkedServiceService,
        user_service: UserService,
        id_factory: Callable[[], str],
        clock: Callable[[], datetime],
    ) -> None:
        """Store workspace resolution, validation, persistence, and clock."""

        self._repository = repository
        self._tenant_service = tenant_service
        self._linked_service_service = linked_service_service
        self._user_service = user_service
        self._id_factory = id_factory
        self._clock = clock

    async def create(
        self,
        *,
        user_id: str,
        name: str,
    ) -> WorkspaceDocument:
        """Create a workspace owned by an existing user."""

        await self._user_service.get(user_id=user_id)
        now = self._clock()
        return await self._repository.create(
            workspace=WorkspaceDocument(
                id=self._id_factory(),
                name=name,
                created_at=now,
                updated_at=now,
            ),
            owner_id=user_id,
        )

    async def list_for_user(self, *, user_id: str) -> list[WorkspaceDocument]:
        """Return workspaces accessible to an existing user."""

        await self._user_service.get(user_id=user_id)
        return await self._repository.list_for_user(user_id=user_id)

    async def describe(
        self,
        *,
        user_id: str,
        workspace_id: str,
    ) -> WorkspaceDocument:
        """Return one Workspace accessible to the requesting User."""

        await self._tenant_service.require_access(
            user_id=user_id,
            workspace_id=workspace_id,
        )
        return await self._repository.get_workspace(workspace_id=workspace_id)

    async def update(
        self,
        *,
        user_id: str,
        workspace_id: str,
        name: str,
    ) -> WorkspaceDocument:
        """Update the mutable metadata for one accessible Workspace."""

        current = await self.describe(
            user_id=user_id,
            workspace_id=workspace_id,
        )
        return await self._repository.update_workspace(
            workspace=replace(
                current,
                name=name,
                updated_at=self._clock(),
            ),
        )
