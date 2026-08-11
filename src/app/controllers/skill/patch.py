"""Controller for patching skills."""

from __future__ import annotations

from src.app.schemas.skill import SkillPatchRequest, SkillResponse
from src.app.services.instructions import InstructionUpdate
from src.app.services.skills import SkillService


class SkillPatchController:
    """Apply content and enabled-state changes to one skill."""

    def __init__(self, *, skill_service: SkillService) -> None:
        """Store the skill application service."""
        self._skill_service = skill_service

    async def patch(
        self,
        *,
        user_id: str,
        skill_id: str,
        payload: SkillPatchRequest,
        requested_workspace_id: str | None = None,
    ) -> SkillResponse:
        """Apply supplied content and enabled-state changes."""
        if payload.has_content_changes():
            metadata = (
                payload.metadata.model_dump(exclude_none=True)
                if payload.metadata is not None
                else None
            )
            assert payload.expected_version is not None
            await self._skill_service.update(
                user_id=user_id,
                skill_id=skill_id,
                requested_workspace_id=requested_workspace_id,
                payload=InstructionUpdate(
                    expected_version=payload.expected_version,
                    name=payload.name,
                    description=payload.description,
                    instructions=payload.instructions,
                    metadata=metadata,
                ),
            )
        if payload.enabled is not None:
            await self._skill_service.set_enabled(
                user_id=user_id,
                skill_id=skill_id,
                enabled=payload.enabled,
                requested_workspace_id=requested_workspace_id,
            )
        document = await self._skill_service.describe(
            user_id=user_id,
            skill_id=skill_id,
            requested_workspace_id=requested_workspace_id,
        )
        return SkillResponse.model_validate(document)
