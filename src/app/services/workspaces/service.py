"""Application service for workspace execution defaults."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from src.app.models.execution import ModelTarget
from src.app.models.workspace import WorkspaceDefaults
from src.app.models.pipeline import PipelineHarness
from src.app.repositories.workspaces import WorkspaceRepository
from src.app.services.linked_services import LinkedServiceService
from src.app.services.shared.tenant import TenantService


class WorkspaceService:
    """Read and replace optional defaults for one workspace."""

    def __init__(
        self,
        *,
        repository: WorkspaceRepository,
        tenant_service: TenantService,
        linked_service_service: LinkedServiceService,
        clock: Callable[[], datetime],
    ) -> None:
        """Store workspace resolution, validation, persistence, and clock."""

        self._repository = repository
        self._tenant_service = tenant_service
        self._linked_service_service = linked_service_service
        self._clock = clock

    async def get_defaults(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
    ) -> WorkspaceDefaults:
        """Return configured or fully inherited defaults for one workspace."""

        workspace_id = await self._workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        defaults = await self._repository.get(workspace_id=workspace_id)
        if defaults is not None:
            return defaults
        return WorkspaceDefaults(
            workspace_id=workspace_id,
            model_target=None,
            harness=None,
            updated_at=self._clock(),
        )

    async def replace_defaults(
        self,
        *,
        user_id: str,
        model_target: ModelTarget | None,
        harness: PipelineHarness | None,
        requested_workspace_id: str | None = None,
    ) -> WorkspaceDefaults:
        """Replace all workspace overrides after validating model routing."""

        workspace_id = await self._workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        if model_target is not None:
            await self._linked_service_service.require_available_selection(
                workspace_id=workspace_id,
                service_id=model_target.linked_service_id,
                model_id=model_target.model_id,
            )
        return await self._repository.replace(
            defaults=WorkspaceDefaults(
                workspace_id=workspace_id,
                model_target=model_target,
                harness=harness,
                updated_at=self._clock(),
            ),
        )

    async def _workspace_id(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None,
    ) -> str:
        """Resolve the workspace selected for this configuration operation."""

        tenant = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        return tenant.workspace_id
