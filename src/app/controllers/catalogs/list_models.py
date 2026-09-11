"""Controller for listing catalog models."""

from src.app.schemas.catalog import (
    CatalogModelListResponse,
    CatalogModelSummaryResponse,
)
from src.app.services.catalogs import StaticCatalogService


class CatalogListModelsController:
    """List static logical models without Project availability state."""

    def list_models(self) -> CatalogModelListResponse:
        """Return logical models without Project availability state."""

        models = self._static_catalog_service.list_models()
        items = [
            CatalogModelSummaryResponse(
                id=model.id,
                name=model.name,
                vendor=model.vendor,
                family=model.family,
                description=model.description,
                released_at=model.released_at,
                capabilities=set(model.capabilities),
                status=model.status,
                tags=list(model.tags),
            )
            for model in models
        ]
        return CatalogModelListResponse(items=items, total=len(items))

    _static_catalog_service: StaticCatalogService