"""Controller for listing loop definitions."""

from __future__ import annotations

from src.app.schemas.loop import LoopListResponse, LoopResponse
from src.app.services.loops.service import LoopService


class LoopListController:
    """Return one page of loop definitions."""

    def __init__(self, *, loop_service: LoopService) -> None:
        """Store the loop application service."""
        self._loop_service = loop_service

    async def list(
        self,
        *,
        user_id: str,
        offset: int,
        requested_workspace_id: str | None = None,
    ) -> LoopListResponse:
        """Return one loop page."""
        documents, total = await self._loop_service.list(
            user_id=user_id,
            offset=offset,
            requested_workspace_id=requested_workspace_id,
        )
        return LoopListResponse(
            items=[LoopResponse.model_validate(item) for item in documents],
            total=total,
        )
