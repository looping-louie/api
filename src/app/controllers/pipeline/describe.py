"""Controller for describing one pipeline definition."""

from __future__ import annotations

from src.app.schemas.pipeline import PipelineResponse
from src.app.services.pipelines.service import PipelineService

from .utils import pipeline_details_response


class PipelineDescribeController:
    """Return one complete pipeline definition."""

    def __init__(self, *, pipeline_service: PipelineService) -> None:
        """Store the pipeline application service."""
        self._pipeline_service = pipeline_service

    async def get(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        requested_workspace_id: str | None = None,
    ) -> PipelineResponse:
        """Return one complete pipeline."""
        details = await self._pipeline_service.describe(
            user_id=user_id,
            pipeline_id=pipeline_id,
            requested_workspace_id=requested_workspace_id,
        )
        return pipeline_details_response(details)
