"""Controller for listing pipeline changelog entries."""

from __future__ import annotations

from src.app.schemas.pipeline import (
    PipelineChangelogEntryResponse,
    PipelineChangelogListResponse,
)
from src.app.services.pipelines.service import PipelineService


class PipelineListChangelogController:
    """Return one page of pipeline changelog entries."""

    def __init__(self, *, pipeline_service: PipelineService) -> None:
        """Store the pipeline application service."""
        self._pipeline_service = pipeline_service

    async def list_changelog(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        offset: int,
        requested_project_id: str | None = None,
    ) -> PipelineChangelogListResponse:
        """Return one newest-first pipeline changelog page."""
        entries, total = await self._pipeline_service.list_changelog(
            user_id=user_id,
            pipeline_id=pipeline_id,
            offset=offset,
            requested_project_id=requested_project_id,
        )
        return PipelineChangelogListResponse(
            items=[
                PipelineChangelogEntryResponse.model_validate(entry)
                for entry in entries
            ],
            total=total,
        )
