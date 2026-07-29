"""Controller for listing skills."""

from __future__ import annotations

from src.app.schemas.skill import SkillListResponse, SkillSummaryResponse
from src.app.services.skill_service import SkillService


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
    ) -> SkillListResponse:
        """List skill summaries available in a workspace."""
        summaries = await self._skill_service.list(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            search=search,
        )
        items = [SkillSummaryResponse.model_validate(item) for item in summaries]
        return SkillListResponse(items=items, total=len(items))
