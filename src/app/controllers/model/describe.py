"""Controller for describing one curated model."""

from __future__ import annotations

from src.app.schemas.model import ModelResponse
from src.app.services.model_service import ModelCatalogService


class ModelDescribeController:
    """Return one curated model and its workspace availability."""

    def __init__(self, *, model_catalog_service: ModelCatalogService) -> None:
        """Store the model catalog application service."""
        self._model_catalog_service = model_catalog_service

    async def describe(
        self,
        *,
        user_id: str,
        model_id: str,
        requested_workspace_id: str | None = None,
    ) -> ModelResponse:
        """Return one curated model and its workspace availability."""
        model = await self._model_catalog_service.describe(
            user_id=user_id,
            model_id=model_id,
            requested_workspace_id=requested_workspace_id,
        )
        return ModelResponse.model_validate(model)
