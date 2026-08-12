"""Controller for describing one persona."""

from __future__ import annotations

from src.app.schemas.persona import PersonaResponse
from src.app.services.personas import PersonaService


class PersonaDescribeController:
    """Return one complete persona visible in a workspace."""

    def __init__(self, *, persona_service: PersonaService) -> None:
        """Store the persona application service."""
        self._persona_service = persona_service

    async def describe(
        self,
        *,
        user_id: str,
        persona_id: str,
        requested_workspace_id: str | None = None,
    ) -> PersonaResponse:
        """Return one complete persona visible in a workspace."""
        document = await self._persona_service.describe(
            user_id=user_id,
            persona_id=persona_id,
            requested_workspace_id=requested_workspace_id,
        )
        return PersonaResponse.model_validate(document)
