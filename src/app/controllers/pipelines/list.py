"""Controller for listing pipeline definitions."""

from __future__ import annotations

from src.app.schemas.pipeline import PipelineListResponse
from src.app.services.pipelines.service import PipelineService

from .utils import pipeline_details_response


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
        requested_project_id: str | None = None,
    ) -> PipelineListResponse:
        """Return one filtered pipeline page."""
        details, total = await self._pipeline_service.list_details(
            user_id=user_id,
            offset=offset,
            status=status,
            search=search,
            requested_project_id=requested_project_id,
        )
        return PipelineListResponse(
            items=[pipeline_details_response(item) for item in details],
            total=total,
        )
