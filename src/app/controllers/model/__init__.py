"""Controllers for curated model HTTP operations."""

from src.app.services.models.service import ModelCatalogService

from .describe import ModelDescribeController
from .list import ModelListController


class ModelController(ModelListController, ModelDescribeController):
    """Compatibility composition of the endpoint-specific controllers."""

    def __init__(self, *, model_catalog_service: ModelCatalogService) -> None:
        """Initialize each controller with the shared catalog service."""
        ModelListController.__init__(
            self,
            model_catalog_service=model_catalog_service,
        )
        ModelDescribeController.__init__(
            self,
            model_catalog_service=model_catalog_service,
        )


__all__ = [
    "ModelController",
    "ModelDescribeController",
    "ModelListController",
]
