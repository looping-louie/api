"""Controller for listing catalog providers."""

from src.app.schemas.catalog import (
    CatalogProviderOfferingResponse,
    CatalogProviderResponse,
)
from src.app.services.catalogs import StaticCatalogService


class CatalogListProvidersController:
    """List static provider types without Project configuration state."""

    def list_providers(self) -> list[CatalogProviderResponse]:
        """Return provider types without Project configuration state."""

        return [
            CatalogProviderResponse(
                id=provider.id,
                name=provider.name,
                description=provider.description,
                logo_url=provider.logo_url,
                requires_api_key=provider.requires_api_key,
                default_base_url=provider.default_base_url,
                model_catalog_note=provider.model_catalog_note,
                offerings=[
                    CatalogProviderOfferingResponse.model_validate(offering)
                    for offering in provider.offerings
                ],
            )
            for provider in self._static_catalog_service.list_providers()
        ]

    _static_catalog_service: StaticCatalogService