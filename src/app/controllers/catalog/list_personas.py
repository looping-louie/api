"""Controller for listing catalog Personas."""

from src.app.schemas.catalog import (
    CatalogInstructionMetadataResponse,
    CatalogPersonaResponse,
)
from src.app.services.catalogs import StaticCatalogService

from .utils import catalog_version


class CatalogListPersonasController:
    """List static Personas without Project availability state."""

    def list_personas(self) -> list[CatalogPersonaResponse]:
        """Return built-in Personas without Project availability state."""

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
                catalog_version=catalog_version(persona.catalog_version),
                deprecated=persona.deprecated,
                category=persona.category,
                skill_ids=list(persona.skill_ids),
                default_for=set(persona.default_for),
            )
            for persona in self._static_catalog_service.list_personas()
        ]

    _static_catalog_service: StaticCatalogService