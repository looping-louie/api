"""Controller for listing personas."""

from __future__ import annotations

from src.app.schemas.persona import PersonaListResponse, PersonaSummaryResponse
from src.app.services.persona_service import PersonaService


class PersonaListController:
    """List persona summaries available in a workspace."""

    def __init__(self, *, persona_service: PersonaService) -> None:
        """Store the persona application service."""
        self._persona_service = persona_service

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
        search: str | None = None,
    ) -> PersonaListResponse:
        """List persona summaries available in a workspace."""
        summaries = await self._persona_service.list(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            search=search,
        )
        items = [PersonaSummaryResponse.model_validate(item) for item in summaries]
        return PersonaListResponse(items=items, total=len(items))
