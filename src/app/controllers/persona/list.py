"""Controller for listing personas."""

from __future__ import annotations

from collections.abc import Sequence

from src.app.catalogs.instructions import (
    CATALOG_INSTRUCTION_PAGE_SIZE,
    CatalogInstructionCategory,
    CatalogInstructionSort,
    CatalogInstructionStatus,
)
from src.app.schemas.persona import PersonaListResponse, PersonaSummaryResponse
from src.app.services.personas import PersonaService


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
        status: CatalogInstructionStatus | None = None,
        categories: Sequence[CatalogInstructionCategory] = (),
        sort: CatalogInstructionSort | None = None,
        offset: int = 0,
    ) -> PersonaListResponse:
        """List persona summaries available in a workspace."""
        page = await self._persona_service.list(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            search=search,
            status=status,
            categories=categories,
            sort=sort,
            offset=offset,
            limit=CATALOG_INSTRUCTION_PAGE_SIZE,
        )
        items = [
            PersonaSummaryResponse.model_validate(item)
            for item in page.items
        ]
        return PersonaListResponse(items=items, total=page.total)
