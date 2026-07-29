"""Controller for deleting skills."""

from __future__ import annotations

from src.app.schemas.common import DeleteResponse
from src.app.services.skill_service import SkillService


class SkillDeleteController:
    """Delete one owned custom skill."""

    def __init__(self, *, skill_service: SkillService) -> None:
        """Store the skill application service."""
        self._skill_service = skill_service

    async def delete(
        self,
        *,
        user_id: str,
        skill_id: str,
        requested_workspace_id: str | None = None,
    ) -> DeleteResponse:
        """Delete an owned custom skill."""
        await self._skill_service.delete(
            user_id=user_id,
            skill_id=skill_id,
            requested_workspace_id=requested_workspace_id,
        )
        return DeleteResponse()
