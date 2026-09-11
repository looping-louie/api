"""Controller for describing one skill."""

from __future__ import annotations

from src.app.schemas.skill import SkillResponse
from src.app.services.skills import SkillService


class SkillDescribeController:
    """Return one complete skill visible to a user."""

    def __init__(self, *, skill_service: SkillService) -> None:
        """Store the skill application service."""
        self._skill_service = skill_service

    async def describe(
        self,
        *,
        user_id: str,
        skill_id: str,
    ) -> SkillResponse:
        """Return one complete skill visible to a user."""
        document = await self._skill_service.describe(
            user_id=user_id,
            skill_id=skill_id,
        )
        return SkillResponse.model_validate(document)
