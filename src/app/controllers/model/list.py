"""Controller for listing curated models."""

from __future__ import annotations

from collections.abc import Sequence

from src.app.catalogs.models import (
    ModelCapability,
    ModelLab,
    ModelSort,
    ModelStatus,
)
from src.app.catalogs.providers import ProviderId
from src.app.schemas.model import ModelListResponse, ModelSummaryResponse
from src.app.services.models.catalog import ModelCatalogService


MODEL_PAGE_SIZE = 24


class ModelListController:
    """List curated models and their workspace availability."""

    def __init__(self, *, model_catalog_service: ModelCatalogService) -> None:
        """Store the model catalog application service."""
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
        """List curated models and their workspace availability."""
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
        page = models[offset : offset + MODEL_PAGE_SIZE]
        items = [ModelSummaryResponse.model_validate(model) for model in page]
        return ModelListResponse(items=items, total=len(models))
