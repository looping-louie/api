"""Controller for describing one pipeline definition."""

from __future__ import annotations

from src.app.schemas.pipeline import PipelineResponse
from src.app.services.pipelines.service import PipelineService


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
        document = await self._pipeline_service.get(
            user_id=user_id,
            pipeline_id=pipeline_id,
            requested_workspace_id=requested_workspace_id,
        )
        return PipelineResponse.model_validate(document)
