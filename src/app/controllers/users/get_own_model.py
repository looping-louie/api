"""Controller for describing a model available to the current User."""

from src.app.schemas.model import ModelResponse
from src.app.services.models.catalog import ModelCatalogService


class UserGetOwnModelController:
    """Describe one curated model and its current User availability."""

    async def describe(self, *, user_id: str, model_id: str) -> ModelResponse:
        """Return one model and its availability for the current User."""

        model = await self._model_catalog_service.describe(
            user_id=user_id,
            model_id=model_id,
        )
        return ModelResponse.model_validate(model)

    _model_catalog_service: ModelCatalogService
