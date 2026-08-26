"""Controller for static catalog list operations."""

from src.app.catalogs.models import CATALOG_INDEX

from src.app.schemas.catalog import (
    CatalogInstructionMetadataResponse,
    CatalogModelListResponse,
    CatalogModelPricingResponse,
    CatalogModelSummaryResponse,
    CatalogPersonaResponse,
    CatalogProviderResponse,
    CatalogSkillResponse,
    CatalogSkillStrictnessResponse,
)
from src.app.schemas.shared import PositiveInteger
from src.app.services.catalogs import StaticCatalogService


class CatalogController:
    """Translate static catalog entries into HTTP response schemas."""

    def __init__(
        self,
        *,
        static_catalog_service: StaticCatalogService,
    ) -> None:
        """Store the static catalog application service."""

        self._static_catalog_service = static_catalog_service

    def list_models(self) -> CatalogModelListResponse:
        """Return logical models without workspace availability state."""

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
                provider_ids=self._static_catalog_service.provider_ids(model),
                deployment_count=len(
                    CATALOG_INDEX.deployments_for_model(model.id)
                ),
                starting_price=(
                    CatalogModelPricingResponse.model_validate(price)
                    if (
                        price := self._static_catalog_service.starting_price(model)
                    )
                    else None
                ),
                tags=list(model.tags),
            )
            for model in models
        ]
        return CatalogModelListResponse(items=items, total=len(items))

    def list_providers(self) -> list[CatalogProviderResponse]:
        """Return provider types without workspace configuration state."""

        return [
            CatalogProviderResponse.model_validate(provider)
            for provider in self._static_catalog_service.list_providers()
        ]

    def list_personas(self) -> list[CatalogPersonaResponse]:
        """Return built-in Personas without workspace availability state."""

        return [
            CatalogPersonaResponse(
                id=persona.id,
                name=persona.name,
                description=persona.description,
                instructions=persona.instructions,
                metadata=CatalogInstructionMetadataResponse(
                    applies_when=list(persona.metadata.applies_when),
                    applies_to=set(persona.metadata.applies_to),
                ),
                enabled_by_default=persona.enabled_by_default,
                catalog_version=self._catalog_version(persona.catalog_version),
                deprecated=persona.deprecated,
                category=persona.category,
                skill_ids=list(persona.skill_ids),
                default_for=set(persona.default_for),
            )
            for persona in self._static_catalog_service.list_personas()
        ]

    def list_skills(self) -> list[CatalogSkillResponse]:
        """Return built-in Skills without workspace availability state."""

        return [
            CatalogSkillResponse(
                id=skill.id,
                name=skill.name,
                description=skill.description,
                instructions=skill.instructions,
                metadata=CatalogInstructionMetadataResponse(
                    applies_when=list(skill.metadata.applies_when),
                    applies_to=set(skill.metadata.applies_to),
                ),
                enabled_by_default=skill.enabled_by_default,
                catalog_version=self._catalog_version(skill.catalog_version),
                deprecated=skill.deprecated,
                category=skill.category,
                reviewer_default_strictness=(
                    CatalogSkillStrictnessResponse.model_validate(
                        skill.reviewer_default_strictness
                    )
                    if skill.reviewer_default_strictness is not None
                    else None
                ),
                phase=skill.phase,
                artifacts=list(skill.artifacts),
                output=skill.output,
            )
            for skill in self._static_catalog_service.list_skills()
        ]

    @staticmethod
    def _catalog_version(value: int | None) -> PositiveInteger:
        """Return the required positive version for a packaged definition."""

        if value is None:
            raise ValueError('Packaged catalog definitions require a version.')
        return value
