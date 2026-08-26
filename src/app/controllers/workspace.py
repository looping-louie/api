"""HTTP controller for workspaces."""

from __future__ import annotations

from src.app.models.workspace import WorkspaceDocument
from src.app.schemas.workspace import (
    WorkspaceCreateRequest,
    WorkspacePatchRequest,
    WorkspaceResponse,
)
from src.app.services.workspaces import WorkspaceService


class WorkspaceController:
    """Translate Workspace HTTP contracts to application operations."""

    def __init__(self, *, service: WorkspaceService) -> None:
        """Store the workspace application service."""

        self._service = service

    async def create(
        self,
        *,
        user_id: str,
        payload: WorkspaceCreateRequest,
    ) -> WorkspaceResponse:
        """Create one Workspace owned by the requesting User."""

        return self._workspace_response(await self._service.create(
            user_id=user_id,
            name=payload.name,
        ))

    async def list_for_user(self, *, user_id: str) -> list[WorkspaceResponse]:
        """Return all Workspaces available to the requesting User."""

        return [
            self._workspace_response(workspace)
            for workspace in await self._service.list_for_user(user_id=user_id)
        ]

    async def describe(
        self,
        *,
        user_id: str,
        workspace_id: str,
    ) -> WorkspaceResponse:
        """Return one Workspace accessible to the requesting User."""

        return self._workspace_response(await self._service.describe(
            user_id=user_id,
            workspace_id=workspace_id,
        ))

    async def patch(
        self,
        *,
        user_id: str,
        workspace_id: str,
        payload: WorkspacePatchRequest,
    ) -> WorkspaceResponse:
        """Update mutable metadata for one accessible Workspace."""

        return self._workspace_response(await self._service.update(
            user_id=user_id,
            workspace_id=workspace_id,
            name=payload.name,
        ))

    @staticmethod
    def _workspace_response(workspace: WorkspaceDocument) -> WorkspaceResponse:
        """Map a workspace document to its public representation."""

        return WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
