"""Controller for patching pipeline definitions."""

from __future__ import annotations

from src.app.schemas.pipeline import (
    PipelinePatchRequest,
    PipelineResponse,
)
from src.app.services.pipelines.service import PipelineService
from src.app.services.pipelines.types import PipelinePatch

from .utils import pipeline_details_response, pipeline_steps


class PipelinePatchController:
    """Apply supplied fields to one pipeline definition."""

    def __init__(self, *, pipeline_service: PipelineService) -> None:
        """Store the pipeline application service."""
        self._pipeline_service = pipeline_service

    async def patch(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        payload: PipelinePatchRequest,
        requested_workspace_id: str | None = None,
    ) -> PipelineResponse:
        """Apply supplied mutable pipeline fields."""
        document = await self._pipeline_service.patch(
            user_id=user_id,
            pipeline_id=pipeline_id,
            requested_workspace_id=requested_workspace_id,
            payload=PipelinePatch(
                provided_fields=frozenset(payload.model_fields_set),
                name=payload.name,
                description=payload.description,
                enabled=payload.enabled,
                steps=(
                    pipeline_steps(payload.steps)
                    if payload.steps is not None
                    else None
                ),
            ),
        )
        details = await self._pipeline_service.describe(
            user_id=user_id,
            pipeline_id=document.id,
            requested_workspace_id=requested_workspace_id,
        )
        return pipeline_details_response(details)
