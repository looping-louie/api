"""Controllers for static catalog HTTP operations."""

from src.app.services.catalogs import StaticCatalogService

from .list_models import CatalogListModelsController
from .list_personas import CatalogListPersonasController
from .list_providers import CatalogListProvidersController
from .list_skills import CatalogListSkillsController


class CatalogController(
    CatalogListModelsController,
    CatalogListPersonasController,
    CatalogListProvidersController,
    CatalogListSkillsController,
):
    """Compose endpoint-specific static catalog controllers."""

    def __init__(
        self,
        *,
        static_catalog_service: StaticCatalogService,
    ) -> None:
        """Store the static catalog application service."""

        self._static_catalog_service = static_catalog_service


__all__ = [
    'CatalogController',
    'CatalogListModelsController',
    'CatalogListPersonasController',
    'CatalogListProvidersController',
    'CatalogListSkillsController',
]