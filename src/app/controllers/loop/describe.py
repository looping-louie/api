"""Controller for describing one loop definition."""

from __future__ import annotations

from src.app.schemas.loop import LoopResponse
from src.app.services.loops.service import LoopService


class LoopDescribeController:
    """Return one complete loop definition."""

    def __init__(self, *, loop_service: LoopService) -> None:
        """Store the loop application service."""
        self._loop_service = loop_service

    async def get(
        self,
        *,
        user_id: str,
        loop_id: str,
        requested_workspace_id: str | None = None,
    ) -> LoopResponse:
        """Return one loop."""
        document = await self._loop_service.get(
            user_id=user_id,
            loop_id=loop_id,
            requested_workspace_id=requested_workspace_id,
        )
        return LoopResponse.model_validate(document)
