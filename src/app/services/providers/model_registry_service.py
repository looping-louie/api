"""Model catalog queries required by provider services."""

from collections.abc import Sequence
from typing import Protocol

from src.app.catalogs.models import (
    MODEL_CATALOG,
    ModelCatalogEntry,
    ModelStatus,
)


class ModelRegistryService(Protocol):
    """Provides model information grouped by provider."""

    def count_by_provider(self, provider: str) -> int:
        """Return the number of selectable logical models for a provider."""
        ...


class CatalogModelRegistryService:
    """Model registry backed by the curated Looping Louie catalog."""

    def __init__(
        self,
        catalog: Sequence[ModelCatalogEntry] = MODEL_CATALOG,
    ) -> None:
        self._catalog = tuple(catalog)

    def count_by_provider(self, provider: str) -> int:
        """Count active logical models exposed through one provider."""

        provider_id = provider.strip().casefold()

        return sum(
            1
            for model in self._catalog
            if self._is_available_through_provider(
                model=model,
                provider_id=provider_id,
            )
        )

    @staticmethod
    def _is_available_through_provider(
        *,
        model: ModelCatalogEntry,
        provider_id: str,
    ) -> bool:
        if model.status == ModelStatus.DEPRECATED:
            return False

        return any(
            deployment.provider_id.value == provider_id
            and deployment.status != ModelStatus.DEPRECATED
            for deployment in model.deployments
        )


class StaticModelRegistryService:
    """Small configurable registry retained for focused tests."""

    def __init__(self, counts: dict[str, int] | None = None) -> None:
        self._counts = {
            provider.strip().casefold(): max(0, count)
            for provider, count in (counts or {}).items()
        }

    def count_by_provider(self, provider: str) -> int:
        """Return the configured model count or zero."""

        return self._counts.get(
            provider.strip().casefold(),
            0,
        )
