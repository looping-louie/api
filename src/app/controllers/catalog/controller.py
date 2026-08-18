"""Controller for static catalog list operations."""

from src.app.schemas.catalog import (
    CatalogModelListResponse,
    CatalogModelPricingResponse,
    CatalogModelSummaryResponse,
    CatalogProviderResponse,
)
from src.app.services.catalog import CatalogService


class CatalogController:
    """Translate static catalog entries into HTTP response schemas."""

    def __init__(self, *, catalog_service: CatalogService) -> None:
        """Store the static catalog application service."""

        self._catalog_service = catalog_service

    def list_models(self) -> CatalogModelListResponse:
        """Return logical models without workspace availability state."""

        models = self._catalog_service.list_models()
        items = [
            CatalogModelSummaryResponse(
                id=model.id,
                name=model.name,
                vendor=model.vendor,
                family=model.family,
                description=model.description,
                released_at=model.released_at,
                capabilities=model.capabilities,
                status=model.status,
                provider_ids=self._catalog_service.provider_ids(model),
                deployment_count=len(model.deployments),
                starting_price=(
                    CatalogModelPricingResponse.model_validate(price)
                    if (price := self._catalog_service.starting_price(model))
                    else None
                ),
                tags=list(model.tags),
            )
            for model in models
        ]
        return CatalogModelListResponse(items=items, total=len(items))

    def list_providers(self) -> list[CatalogProviderResponse]:
        """Return provider types without workspace configuration state."""

        return [
            CatalogProviderResponse.model_validate(provider)
            for provider in self._catalog_service.list_providers()
        ]