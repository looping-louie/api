"""Controller for creating personas."""

from __future__ import annotations

from src.app.schemas.persona import PersonaCreateRequest, PersonaResponse
from src.app.services.persona_service import PersonaCreate, PersonaService


class PersonaCreateController:
    """Create one persona directly or from an available source."""

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
        """Create a new persona directly or by copying a source."""
        if payload.source_persona_id is not None:
            document = await self._persona_service.create_from_source(
                user_id=user_id,
                source_persona_id=payload.source_persona_id,
                name=payload.name,
                requested_workspace_id=requested_workspace_id,
            )
        else:
            assert payload.name is not None
            assert payload.instructions is not None
            document = await self._persona_service.create(
                user_id=user_id,
                requested_workspace_id=requested_workspace_id,
                payload=PersonaCreate(
                    name=payload.name,
                    description=payload.description,
                    instructions=payload.instructions,
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
