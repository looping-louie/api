"""Derived provider-to-model catalog query indexes."""

from collections.abc import Sequence

from ..providers import ProviderCatalogEntry, ProviderId
from .types import ModelCatalogEntry, ModelDeployment, ProviderModelOffering


class CatalogIndex:
    """Expose provider-owned offerings through model-centric queries."""

    def __init__(
        self,
        *,
        models: Sequence[ModelCatalogEntry],
        providers: Sequence[ProviderCatalogEntry],
    ) -> None:
        """Build immutable deployment lookups from catalog declarations."""

        deployments_by_model: dict[str, list[ModelDeployment]] = {
            model.id: []
            for model in models
        }
        offerings_by_model: dict[str, list[ProviderModelOffering]] = {
            model.id: []
            for model in models
        }

        for provider in providers:
            for offering in provider.offerings:
                offerings_by_model[offering.model_id].append(offering)
                deployments_by_model[offering.model_id].append(
                    ModelDeployment(
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

        self._deployments_by_model = {
            model_id: tuple(deployments)
            for model_id, deployments in deployments_by_model.items()
        }
        self._offerings_by_model = {
            model_id: tuple(offerings)
            for model_id, offerings in offerings_by_model.items()
        }

    def deployments_for_model(self, model_id: str) -> tuple[ModelDeployment, ...]:
        """Return deployments for one logical model in provider order."""

        return self._deployments_by_model.get(model_id, ())

    def providers_for_model(self, model_id: str) -> tuple[ProviderId, ...]:
        """Return unique provider IDs for one logical model."""

        return tuple(dict.fromkeys(
            deployment.provider_id
            for deployment in self.deployments_for_model(model_id)
        ))

    def offerings_for_model(
        self,
        model_id: str,
    ) -> tuple[ProviderModelOffering, ...]:
        """Return provider-owned offerings for one logical model."""

        return self._offerings_by_model.get(model_id, ())