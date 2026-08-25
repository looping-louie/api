"""Controller for creating pipeline definitions."""

from __future__ import annotations

from src.app.schemas.pipeline import (
    PipelineCreateRequest,
    PipelineResponse,
)
from src.app.models.execution import ModelTarget
from src.app.services.pipelines.service import PipelineService
from src.app.services.pipelines.types import PipelineCreate

from .utils import pipeline_details_response, pipeline_harness, pipeline_steps


class PipelineCreateController:
    """Create one pipeline definition."""

    def __init__(self, *, pipeline_service: PipelineService) -> None:
        """Store the pipeline application service."""
        self._pipeline_service = pipeline_service

    async def create(
        self,
        *,
        user_id: str,
        payload: PipelineCreateRequest,
        requested_workspace_id: str | None = None,
    ) -> PipelineResponse:
        """Create one enabled pipeline."""
        document = await self._pipeline_service.create(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            payload=PipelineCreate(
                name=payload.name,
                description=payload.description,
                steps=pipeline_steps(payload.steps),
                model_target=(
                    ModelTarget(
                        linked_service_id=payload.model_target.linked_service_id,
                        model_id=payload.model_target.model_id,
                    )
                    if payload.model_target is not None
                    else None
                ),
                harness=pipeline_harness(payload.harness),
            ),
        )
        details = await self._pipeline_service.describe(
            user_id=user_id,
            pipeline_id=document.id,
            requested_workspace_id=requested_workspace_id,
        )
        return pipeline_details_response(details)
