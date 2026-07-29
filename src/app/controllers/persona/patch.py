"""Controller for patching personas."""

from __future__ import annotations

from src.app.schemas.persona import PersonaPatchRequest, PersonaResponse
from src.app.services.persona_service import PersonaService, PersonaUpdate


class PersonaPatchController:
    """Apply content and enabled-state changes to one persona."""

    def __init__(self, *, persona_service: PersonaService) -> None:
        """Store the persona application service."""
        self._persona_service = persona_service

    async def patch(
        self,
        *,
        user_id: str,
        persona_id: str,
        payload: PersonaPatchRequest,
        requested_workspace_id: str | None = None,
    ) -> PersonaResponse:
        """Apply supplied content and enabled-state changes."""
        if payload.has_content_changes():
            assert payload.expected_version is not None
            await self._persona_service.update(
                user_id=user_id,
                persona_id=persona_id,
                requested_workspace_id=requested_workspace_id,
                payload=PersonaUpdate(
                    expected_version=payload.expected_version,
                    name=payload.name,
                    description=payload.description,
                    instructions=payload.instructions,
                    metadata=payload.metadata,
                    skill_ids=(
                        tuple(payload.skill_ids)
                        if payload.skill_ids is not None
                        else None
                    ),
                ),
            )
        if payload.enabled is not None:
            await self._persona_service.set_enabled(
                user_id=user_id,
                persona_id=persona_id,
                enabled=payload.enabled,
                requested_workspace_id=requested_workspace_id,
            )
        document = await self._persona_service.describe(
            user_id=user_id,
            persona_id=persona_id,
            requested_workspace_id=requested_workspace_id,
        )
        return PersonaResponse.model_validate(document)
