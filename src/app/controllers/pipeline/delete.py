"""Controller for deleting pipeline definitions."""

from __future__ import annotations

from src.app.schemas.common import DeleteResponse
from src.app.services.pipeline_service import PipelineService


class PipelineDeleteController:
    """Archive one pipeline definition."""

    def __init__(self, *, pipeline_service: PipelineService) -> None:
        """Store the pipeline application service."""
        self._pipeline_service = pipeline_service

    async def delete(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        requested_workspace_id: str | None = None,
    ) -> DeleteResponse:
        """Archive one pipeline definition."""
        await self._pipeline_service.archive(
            user_id=user_id,
            pipeline_id=pipeline_id,
            requested_workspace_id=requested_workspace_id,
        )
        return DeleteResponse()
