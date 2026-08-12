"""Controller for listing pipeline definitions."""

from __future__ import annotations

from src.app.schemas.pipeline import PipelineListResponse, PipelineResponse
from src.app.services.pipelines.service import PipelineService


class PipelineListController:
    """Return one filtered page of pipeline definitions."""

    def __init__(self, *, pipeline_service: PipelineService) -> None:
        """Store the pipeline application service."""
        self._pipeline_service = pipeline_service

    async def list(
        self,
        *,
        user_id: str,
        offset: int,
        status: str | None,
        search: str | None,
        requested_workspace_id: str | None = None,
    ) -> PipelineListResponse:
        """Return one filtered pipeline page."""
        documents, total = await self._pipeline_service.list(
            user_id=user_id,
            offset=offset,
            status=status,
            search=search,
            requested_workspace_id=requested_workspace_id,
        )
        return PipelineListResponse(
            items=[PipelineResponse.model_validate(item) for item in documents],
            total=total,
        )
