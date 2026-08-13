"""Controller for creating personas."""

from __future__ import annotations

from src.app.schemas.persona import PersonaCreateRequest, PersonaResponse
from src.app.services.personas import PersonaCreate, PersonaService


class PersonaCreateController:
    """Create one persona."""

    def __init__(self, *, persona_service: PersonaService) -> None:
        """Store the persona application service."""
        self._persona_service = persona_service

    async def create(
        self,
        *,
        user_id: str,
        payload: PersonaCreateRequest,
        requested_workspace_id: str | None = None,
    ) -> PersonaResponse:
        """Create a new persona from the supplied content."""
        document = await self._persona_service.create(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            payload=PersonaCreate(
                name=payload.name,
                description=payload.description,
                instructions=payload.instructions,
                model=payload.model,
                metadata=payload.metadata,
                skill_ids=tuple(payload.skill_ids),
            ),
        )
        document = await self._persona_service.describe(
            user_id=user_id,
            persona_id=document.id,
            requested_workspace_id=requested_workspace_id,
        )
        return PersonaResponse.model_validate(document)
