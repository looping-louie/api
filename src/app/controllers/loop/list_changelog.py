"""Controller for listing loop changelog entries."""

from __future__ import annotations

from src.app.schemas.loop import (
    LoopChangelogEntryResponse,
    LoopChangelogListResponse,
)
from src.app.services.loops.service import LoopService


class LoopListChangelogController:
    """Return one page of loop changelog entries."""

    def __init__(self, *, loop_service: LoopService) -> None:
        """Store the loop application service."""
        self._loop_service = loop_service

    async def list_changelog(
        self,
        *,
        user_id: str,
        loop_id: str,
        offset: int,
        requested_workspace_id: str | None = None,
    ) -> LoopChangelogListResponse:
        """Return one newest-first changelog page."""
        entries, total = await self._loop_service.list_changelog(
            user_id=user_id,
            loop_id=loop_id,
            offset=offset,
            requested_workspace_id=requested_workspace_id,
        )
        return LoopChangelogListResponse(
            items=[
                LoopChangelogEntryResponse.model_validate(entry)
                for entry in entries
            ],
            total=total,
        )
