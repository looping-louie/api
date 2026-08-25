"""HTTP controller for workspace execution defaults."""

from __future__ import annotations

from src.app.models.workspace import ModelTarget, WorkspaceDefaults
from src.app.models.pipeline import PipelineHarness
from src.app.schemas.workspace import (
    WorkspaceDefaultsReplaceRequest,
    WorkspaceDefaultsResponse,
)
from src.app.services.workspaces import WorkspaceService


class WorkspaceController:
    """Translate execution-default HTTP contracts to application operations."""

    def __init__(self, *, service: WorkspaceService) -> None:
        """Store the workspace application service."""

        self._service = service

    async def get_defaults(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
    ) -> WorkspaceDefaultsResponse:
        """Return workspace overrides and inherited values."""

        defaults = await self._service.get_defaults(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        return self._response(defaults)

    async def replace_defaults(
        self,
        *,
        user_id: str,
        payload: WorkspaceDefaultsReplaceRequest,
        requested_workspace_id: str | None = None,
    ) -> WorkspaceDefaultsResponse:
        """Replace the workspace's optional model and Harness overrides."""

        defaults = await self._service.replace_defaults(
            user_id=user_id,
            model_target=(
                ModelTarget(
                    linked_service_id=payload.model_target.linked_service_id,
                    model_id=payload.model_target.model_id,
                )
                if payload.model_target is not None
                else None
            ),
            harness=(
                PipelineHarness(
                    kind=payload.harness.kind,
                    version=payload.harness.version,
                    config=payload.harness.config,
                )
                if payload.harness is not None
                else None
            ),
            requested_workspace_id=requested_workspace_id,
        )
        return self._response(defaults)

    @staticmethod
    def _response(
        defaults: WorkspaceDefaults,
    ) -> WorkspaceDefaultsResponse:
        """Convert the domain defaults to their HTTP representation."""

        return WorkspaceDefaultsResponse.model_validate(
            {
                'model_target': (
                    {
                        'linked_service_id': defaults.model_target.linked_service_id,
                        'model_id': defaults.model_target.model_id,
                    }
                    if defaults.model_target is not None
                    else None
                ),
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
