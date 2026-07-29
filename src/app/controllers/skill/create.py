"""Controller for creating skills."""

from __future__ import annotations

from src.app.schemas.skill import SkillCreateRequest, SkillResponse
from src.app.services.shared.instruction_service import InstructionCreate
from src.app.services.skill_service import SkillService


class SkillCreateController:
    """Create one skill directly or from an available source."""

    def __init__(self, *, skill_service: SkillService) -> None:
        """Store the skill application service."""
        self._skill_service = skill_service

    async def create(
        self,
        *,
        user_id: str,
        payload: SkillCreateRequest,
        requested_workspace_id: str | None = None,
    ) -> SkillResponse:
        """Create a new skill directly or by copying a source."""
        if payload.source_skill_id is not None:
            document = await self._skill_service.create_from_source(
                user_id=user_id,
                source_skill_id=payload.source_skill_id,
                name=payload.name,
                requested_workspace_id=requested_workspace_id,
            )
        else:
            assert payload.name is not None
            assert payload.instructions is not None
            document = await self._skill_service.create(
                user_id=user_id,
                requested_workspace_id=requested_workspace_id,
                payload=InstructionCreate(
                    name=payload.name,
                    description=payload.description,
                    instructions=payload.instructions,
                    metadata=payload.metadata.model_dump(exclude_none=True),
                ),
            )
        document = await self._skill_service.describe(
            user_id=user_id,
            skill_id=document.id,
            requested_workspace_id=requested_workspace_id,
        )
        return SkillResponse.model_validate(document)
