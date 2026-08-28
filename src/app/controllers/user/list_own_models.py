"""Controller for listing models available to the current User."""

from collections.abc import Sequence

from src.app.catalogs.models import ModelCapability, ModelLab, ModelSort, ModelStatus
from src.app.catalogs.providers import ProviderId
from src.app.schemas.model import ModelListResponse, ModelSummaryResponse
from src.app.services.models.catalog import ModelCatalogService


class UserListOwnModelsController:
    """List curated models and availability for the current User."""

    async def list(
        self,
        *,
        user_id: str,
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
        """Return one filtered model catalog page for the current User."""

        models = await self._model_catalog_service.list(
            user_id=user_id,
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
        return ModelListResponse(
            items=[ModelSummaryResponse.model_validate(model) for model in page],
            total=len(models),
        )

    _model_catalog_service: ModelCatalogService