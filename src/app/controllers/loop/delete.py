"""Controller for deleting loop definitions."""

from __future__ import annotations

from src.app.schemas.common import DeleteResponse
from src.app.services.loop_service import LoopService


class LoopDeleteController:
    """Delete one loop definition."""

    def __init__(self, *, loop_service: LoopService) -> None:
        """Store the loop application service."""
        self._loop_service = loop_service

    async def delete(
        self,
        *,
        user_id: str,
        loop_id: str,
        requested_workspace_id: str | None = None,
    ) -> DeleteResponse:
        """Delete one loop definition."""
        await self._loop_service.delete(
            user_id=user_id,
            loop_id=loop_id,
            requested_workspace_id=requested_workspace_id,
        )
        return DeleteResponse()
