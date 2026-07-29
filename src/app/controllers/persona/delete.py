"""Controller for deleting personas."""

from __future__ import annotations

from src.app.schemas.common import DeleteResponse
from src.app.services.personas.service import PersonaService


class PersonaDeleteController:
    """Delete one owned custom persona."""

    def __init__(self, *, persona_service: PersonaService) -> None:
        """Store the persona application service."""
        self._persona_service = persona_service

    async def delete(
        self,
        *,
        user_id: str,
        persona_id: str,
        requested_workspace_id: str | None = None,
    ) -> DeleteResponse:
        """Delete an owned custom persona."""
        await self._persona_service.delete(
            user_id=user_id,
            persona_id=persona_id,
            requested_workspace_id=requested_workspace_id,
        )
        return DeleteResponse()
