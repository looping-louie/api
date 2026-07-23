"""Model catalog queries required by provider services."""

from collections.abc import Sequence
from typing import Protocol

from src.app.catalogs.models import (
    MODEL_CATALOG,
    ModelCatalogEntry,
    ModelStatus,
)
from src.app.catalogs.providers import ProviderId


class ModelRegistryService(Protocol):
    """Provides model information grouped by provider."""

    def count_by_provider(self, provider: ProviderId) -> int:
        """Return the number of selectable logical models for a provider."""
        ...


class CatalogModelRegistryService:
    """Model registry backed by the curated Looping Louie catalog."""

    def __init__(
        self,
        catalog: Sequence[ModelCatalogEntry] = MODEL_CATALOG,
    ) -> None:
        self._catalog = tuple(catalog)

    def count_by_provider(self, provider: ProviderId) -> int:
        """Count active logical models exposed through one provider."""

        return sum(
            1
            for model in self._catalog
            if self._is_available_through_provider(
                model=model,
                provider_id=provider,
            )
        )

    @staticmethod
    def _is_available_through_provider(
        *,
        model: ModelCatalogEntry,
        provider_id: ProviderId,
    ) -> bool:
        if model.status == ModelStatus.DEPRECATED:
            return False

        return any(
            deployment.provider_id == provider_id
            and deployment.status != ModelStatus.DEPRECATED
            for deployment in model.deployments
        )
