"""Application service for workspace-independent static catalogs."""

from __future__ import annotations

from collections.abc import Sequence

from src.app.catalogs.models import (
    MODEL_CATALOG,
    ModelCatalogEntry,
    ModelPricing,
    ModelStatus,
)
from src.app.catalogs.providers import PROVIDER_CATALOG, ProviderCatalogEntry


class StaticCatalogService:
    """Expose curated provider and model definitions without workspace state."""

    def __init__(
        self,
        *,
        models: Sequence[ModelCatalogEntry] = MODEL_CATALOG,
        providers: Sequence[ProviderCatalogEntry] = PROVIDER_CATALOG,
    ) -> None:
        """Store the immutable application-owned catalog definitions."""

        self._models = tuple(models)
        self._providers = tuple(providers)

    def list_models(self) -> list[ModelCatalogEntry]:
        """Return non-deprecated logical model definitions."""

        return [
            model
            for model in self._models
            if model.status != ModelStatus.DEPRECATED
        ]

    def list_providers(self) -> list[ProviderCatalogEntry]:
        """Return supported provider types and their static metadata."""

        return list(self._providers)

    @staticmethod
    def provider_ids(model: ModelCatalogEntry) -> list[str]:
        """Return unique provider identifiers in deployment order."""

        return list(dict.fromkeys(
            deployment.provider_id
            for deployment in model.deployments
        ))

    @staticmethod
    def starting_price(model: ModelCatalogEntry) -> ModelPricing | None:
        """Return the lowest active deployment price for a catalog model."""

        prices = [
            deployment.pricing
            for deployment in model.deployments
            if deployment.status != ModelStatus.DEPRECATED
            and deployment.pricing is not None
        ]

        if not prices:
            return None

        return min(
            prices,
            key=lambda price: (
                price.input_per_million_usd
                + price.output_per_million_usd
            ),
        )
