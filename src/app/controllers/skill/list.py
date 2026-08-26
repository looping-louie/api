"""Controller for listing skills."""

from __future__ import annotations

from collections.abc import Sequence

from src.app.catalogs.persona_skills import (
    CATALOG_INSTRUCTION_PAGE_SIZE,
    CatalogInstructionCategory,
    CatalogInstructionSort,
    CatalogInstructionStatus,
)
from src.app.schemas.skill import SkillListResponse, SkillSummaryResponse
from src.app.services.skills import SkillService


class SkillListController:
    """List skill summaries available to one user."""

    def __init__(self, *, skill_service: SkillService) -> None:
        """Store the skill application service."""
        self._skill_service = skill_service

    async def list(
        self,
        *,
        user_id: str,
        search: str | None = None,
        status: CatalogInstructionStatus | None = None,
        categories: Sequence[CatalogInstructionCategory] = (),
        sort: CatalogInstructionSort | None = None,
        offset: int = 0,
    ) -> SkillListResponse:
        """List skill summaries available to one user."""
        page = await self._skill_service.list(
            user_id=user_id,
            search=search,
            status=status,
            categories=categories,
            sort=sort,
            offset=offset,
            limit=CATALOG_INSTRUCTION_PAGE_SIZE,
        )
        items = [
            SkillSummaryResponse.model_validate(item)
            for item in page.items
        ]
        return SkillListResponse(items=items, total=page.total)
