"""Controller for listing catalog Skills."""

from src.app.schemas.catalog import (
    CatalogInstructionMetadataResponse,
    CatalogSkillResponse,
    CatalogSkillStrictnessResponse,
)
from src.app.services.catalogs import StaticCatalogService

from .utils import catalog_version


class CatalogListSkillsController:
    """List static Skills without Project availability state."""

    def list_skills(self) -> list[CatalogSkillResponse]:
        """Return built-in Skills without Project availability state."""

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
                catalog_version=catalog_version(skill.catalog_version),
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

    _static_catalog_service: StaticCatalogService