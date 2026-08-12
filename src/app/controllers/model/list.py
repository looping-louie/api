"""Controller for listing curated models."""

from __future__ import annotations

from src.app.catalogs.models import ModelCapability, ModelStatus
from src.app.catalogs.providers import ProviderId
from src.app.schemas.model import ModelListResponse, ModelSummaryResponse
from src.app.services.models.service import ModelCatalogService


class ModelListController:
    """List curated models and their workspace availability."""

    def __init__(self, *, model_catalog_service: ModelCatalogService) -> None:
        """Store the model catalog application service."""
        self._model_catalog_service = model_catalog_service

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
        provider_id: ProviderId | None = None,
        capability: ModelCapability | None = None,
        model_status: ModelStatus | None = None,
        available: bool | None = None,
        search: str | None = None,
        include_deprecated: bool = False,
    ) -> ModelListResponse:
        """List curated models and their workspace availability."""
        models = await self._model_catalog_service.list(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            provider_id=provider_id,
            capability=capability,
            model_status=model_status,
            available=available,
            search=search,
            include_deprecated=include_deprecated,
        )
        items = [ModelSummaryResponse.model_validate(model) for model in models]
        return ModelListResponse(items=items, total=len(items))
