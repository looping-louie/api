"""HTTP controller for workspace execution defaults."""

from __future__ import annotations

from src.app.models.workspace import WorkspaceDocument
from src.app.models.workspace import WorkspaceDefaults
from src.app.models.pipeline import PipelineHarness
from src.app.schemas.workspace import (
    WorkspaceDefaultsReplaceRequest,
    WorkspaceDefaultsResponse,
    WorkspaceCreateRequest,
    WorkspacePatchRequest,
    WorkspaceResponse,
)
from src.app.services.workspaces import WorkspaceService


class WorkspaceController:
    """Translate execution-default HTTP contracts to application operations."""

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

    async def get_defaults(
        self,
        *,
        user_id: str,
        workspace_id: str,
    ) -> WorkspaceDefaultsResponse:
        """Return workspace overrides and inherited values."""

        defaults = await self._service.get_defaults(
            user_id=user_id,
            workspace_id=workspace_id,
        )
        return self._response(defaults)

    async def replace_defaults(
        self,
        *,
        user_id: str,
        workspace_id: str,
        payload: WorkspaceDefaultsReplaceRequest,
    ) -> WorkspaceDefaultsResponse:
        """Replace the workspace's optional model and Harness overrides."""

        defaults = await self._service.replace_defaults(
            user_id=user_id,
            model_id=payload.model_id,
            harness=(
                PipelineHarness(
                    kind=payload.harness.kind,
                    version=payload.harness.version,
                    config=payload.harness.config,
                )
                if payload.harness is not None
                else None
            ),
            workspace_id=workspace_id,
        )
        return self._response(defaults)

    @staticmethod
    def _response(
        defaults: WorkspaceDefaults,
    ) -> WorkspaceDefaultsResponse:
        """Convert the domain defaults to their HTTP representation."""

        return WorkspaceDefaultsResponse.model_validate(
            {
                'model_id': defaults.model_id,
                'harness': (
                    {
                        'kind': defaults.harness.kind,
                        'version': defaults.harness.version,
                        'config': dict(defaults.harness.config),
                    }
                    if defaults.harness is not None
                    else None
                ),
                'updated_at': defaults.updated_at,
            },
        )

    @staticmethod
    def _workspace_response(workspace: WorkspaceDocument) -> WorkspaceResponse:
        """Map a workspace document to its public representation."""

        return WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
