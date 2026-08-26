"""HTTP controller for workspace execution defaults."""

from __future__ import annotations

from collections.abc import Sequence

from src.app.catalogs.models import (
    ModelCapability,
    ModelLab,
    ModelSort,
    ModelStatus,
)
from src.app.catalogs.providers import ProviderId
from src.app.models.workspace import WorkspaceDocument
from src.app.models.workspace import WorkspaceDefaults
from src.app.models.pipeline import PipelineHarness
from src.app.schemas.model import ModelListResponse, ModelResponse, ModelSummaryResponse
from src.app.schemas.workspace import (
    WorkspaceDefaultsReplaceRequest,
    WorkspaceDefaultsResponse,
    WorkspaceCreateRequest,
    WorkspacePatchRequest,
    WorkspaceResponse,
)
from src.app.services.models.catalog import ModelCatalogService
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


class WorkspaceModelController:
    """Translate Workspace model availability HTTP contracts to application operations."""

    def __init__(self, *, model_catalog_service: ModelCatalogService) -> None:
        """Store the Workspace-aware model catalog service."""

        self._model_catalog_service = model_catalog_service

    async def list(
        self,
        *,
        user_id: str,
        workspace_id: str,
        provider_id: ProviderId | None = None,
        capability: ModelCapability | None = None,
        model_status: ModelStatus | None = None,
        labs: Sequence[ModelLab] = (),
        sort: ModelSort | None = None,
        offset: int = 0,
        available: bool | None = None,
        search: str | None = None,
        include_deprecated: bool = False,
    ) -> ModelListResponse:
        """List curated models and availability for one Workspace."""

        models = await self._model_catalog_service.list(
            user_id=user_id,
            workspace_id=workspace_id,
            provider_id=provider_id,
            capability=capability,
            model_status=model_status,
            labs=labs,
            sort=sort,
            available=available,
            search=search,
            include_deprecated=include_deprecated,
        )
        page = models[offset : offset + 24]
        items = [ModelSummaryResponse.model_validate(model) for model in page]
        return ModelListResponse(items=items, total=len(models))

    async def describe(
        self,
        *,
        user_id: str,
        workspace_id: str,
        model_id: str,
    ) -> ModelResponse:
        """Describe one curated model and availability for one Workspace."""

        model = await self._model_catalog_service.describe(
            user_id=user_id,
            workspace_id=workspace_id,
            model_id=model_id,
        )
        return ModelResponse.model_validate(model)
