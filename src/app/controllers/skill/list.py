"""Controller for listing skills."""

from __future__ import annotations

from collections.abc import Sequence

from src.app.catalogs.skills import SkillCategory, SkillSort, SkillStatus
from src.app.schemas.skill import SkillListResponse, SkillSummaryResponse
from src.app.services.skills import SkillService


SKILL_PAGE_SIZE = 12


class SkillListController:
    """List skill summaries available in a workspace."""

    def __init__(self, *, skill_service: SkillService) -> None:
        """Store the skill application service."""
        self._skill_service = skill_service

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
        search: str | None = None,
        status: SkillStatus | None = None,
        categories: Sequence[SkillCategory] = (),
        sort: SkillSort | None = None,
        offset: int = 0,
    ) -> SkillListResponse:
        """List skill summaries available in a workspace."""
        summaries = await self._skill_service.list(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            search=search,
            status=status,
            categories=categories,
            sort=sort,
        )
        page = summaries[offset : offset + SKILL_PAGE_SIZE]
        items = [SkillSummaryResponse.model_validate(item) for item in page]
        return SkillListResponse(items=items, total=len(summaries))
