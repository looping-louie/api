"""Derived provider-to-model catalog query indexes."""

from collections.abc import Sequence

from ..providers import ProviderCatalogEntry, ProviderId
from .types import ModelCatalogEntry, ModelOffering


class CatalogIndex:
    """Expose provider-owned offerings through model-centric queries."""

    def __init__(
        self,
        *,
        models: Sequence[ModelCatalogEntry],
        providers: Sequence[ProviderCatalogEntry],
    ) -> None:
        """Build immutable offering lookups from catalog declarations."""

        offerings_by_model: dict[str, list[ModelOffering]] = {
            model.id: []
            for model in models
        }

        for provider in providers:
            for offering in provider.offerings:
                offerings_by_model[offering.model_id].append(
                    ModelOffering(
                        provider_id=provider.id,
                        provider_model_id=offering.provider_model_id,
                        endpoint=offering.endpoint,
                        context_window=offering.context_window,
                        max_output_tokens=offering.max_output_tokens,
                        pricing=offering.pricing,
                        status=offering.status,
                        deprecated_at=offering.deprecated_at,
                    )
                )

        self._offerings_by_model = {
            model_id: tuple(offerings)
            for model_id, offerings in offerings_by_model.items()
        }

    def providers_for_model(self, model_id: str) -> tuple[ProviderId, ...]:
        """Return unique provider IDs for one logical model."""

        return tuple(dict.fromkeys(
            offering.provider_id
            for offering in self.offerings_for_model(model_id)
        ))

    def offerings_for_model(
        self,
        model_id: str,
    ) -> tuple[ModelOffering, ...]:
        """Return provider-owned offerings for one logical model."""

        return self._offerings_by_model.get(model_id, ())
