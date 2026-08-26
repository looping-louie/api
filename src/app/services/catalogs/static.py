"""Application service for workspace-independent static catalogs."""

from __future__ import annotations

from collections.abc import Sequence

from src.app.catalogs.models import (
    CATALOG_INDEX,
    MODEL_CATALOG,
    ModelCatalogEntry,
    ModelPricing,
    ModelStatus,
)
from src.app.catalogs.providers import (
    PROVIDER_CATALOG,
    ProviderCatalogEntry,
    ProviderId,
)
from src.app.catalogs.persona_skills.entries import (
    PersonaCatalogEntry,
    SkillCatalogEntry,
)
from src.app.catalogs.persona_skills.loader import (
    PersonaSkillCatalog,
    load_persona_skill_catalog,
)


class StaticCatalogService:
    """Expose curated provider and model definitions without workspace state."""

    def __init__(
        self,
        *,
        models: Sequence[ModelCatalogEntry] = MODEL_CATALOG,
        providers: Sequence[ProviderCatalogEntry] = PROVIDER_CATALOG,
        instruction_catalog: PersonaSkillCatalog | None = None,
    ) -> None:
        """Store the immutable application-owned catalog definitions."""

        self._models = tuple(models)
        self._providers = tuple(providers)
        self._instruction_catalog = (
            instruction_catalog
            if instruction_catalog is not None
            else load_persona_skill_catalog()
        )

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

    def list_personas(self) -> list[PersonaCatalogEntry]:
        """Return application-owned built-in Persona definitions."""

        return list(self._instruction_catalog.personas)

    def list_skills(self) -> list[SkillCatalogEntry]:
        """Return application-owned built-in Skill definitions."""

        return list(self._instruction_catalog.skills)

    @staticmethod
    def provider_ids(model: ModelCatalogEntry) -> list[ProviderId]:
        """Return unique provider identifiers in deployment order."""

        return list(dict.fromkeys(
            CATALOG_INDEX.providers_for_model(model.id)
        ))

    @staticmethod
    def starting_price(model: ModelCatalogEntry) -> ModelPricing | None:
        """Return the lowest active deployment price for a catalog model."""

        prices = [
            deployment.pricing
            for deployment in CATALOG_INDEX.deployments_for_model(model.id)
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
