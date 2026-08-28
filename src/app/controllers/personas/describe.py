"""Controller for describing one persona."""

from __future__ import annotations

from src.app.schemas.persona import PersonaResponse
from src.app.services.personas import PersonaService

from .response import persona_response


class PersonaDescribeController:
    """Return one complete persona visible to a user."""

    def __init__(self, *, persona_service: PersonaService) -> None:
        """Store the persona application service."""
        self._persona_service = persona_service

    async def describe(
        self,
        *,
        user_id: str,
        persona_id: str,
    ) -> PersonaResponse:
        """Return one complete persona visible to a user."""
        document = await self._persona_service.describe(
            user_id=user_id,
            persona_id=persona_id,
        )
        return persona_response(document)
