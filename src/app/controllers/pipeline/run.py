"""Controllers for dependency-aware pipeline execution."""

from src.app.controllers.loop_run.utils import activity_run_response
from src.app.models.activity_run import ActivityRunDocument
from src.app.models.pipeline_run import PipelineRunDocument
from src.app.schemas.pipeline import (
    PipelineRunCreateRequest,
    PipelineRunResponse,
    PipelineRunStepResponse,
)
from src.app.services.pipeline_runs import PipelineRunService


class PipelineRunController:
    """Translate pipeline-run HTTP operations into scheduler service calls."""

    def __init__(self, *, pipeline_run_service: PipelineRunService | None) -> None:
        """Store the optional runtime service used only by run endpoints."""

        self._pipeline_run_service = pipeline_run_service

    async def create_run(
        self, *, user_id: str, pipeline_id: str, payload: PipelineRunCreateRequest,
        requested_workspace_id: str | None = None,
    ) -> PipelineRunResponse:
        """Create one pipeline run and select its first child activity run."""

        document, child = await self._require_service().create(
            user_id=user_id, pipeline_id=pipeline_id, input_text=payload.input,
            requested_workspace_id=requested_workspace_id,
        )
        return self._response(document, child)

    async def get_run(
        self, *, user_id: str, pipeline_id: str, run_id: str,
        requested_workspace_id: str | None = None,
    ) -> PipelineRunResponse:
        """Return one pipeline run and its selected activity run."""

        document, child = await self._require_service().get(
            user_id=user_id, pipeline_id=pipeline_id, run_id=run_id,
            requested_workspace_id=requested_workspace_id,
        )
        return self._response(document, child)

    async def continue_run(
        self, *, user_id: str, pipeline_id: str, run_id: str,
        requested_workspace_id: str | None = None,
    ) -> PipelineRunResponse:
        """Schedule after the current child activity run reaches a terminal state."""

        document, child = await self._require_service().continue_run(
            user_id=user_id, pipeline_id=pipeline_id, run_id=run_id,
            requested_workspace_id=requested_workspace_id,
        )
        return self._response(document, child)

    def _require_service(self) -> PipelineRunService:
        """Return the runtime service when the application configured it."""

        if self._pipeline_run_service is None:
            raise RuntimeError('Pipeline execution is not configured.')
        return self._pipeline_run_service

    @staticmethod
    def _response(
        document: PipelineRunDocument,
        child: ActivityRunDocument | None,
    ) -> PipelineRunResponse:
        """Shape one scheduler result without exposing frozen configuration."""

        return PipelineRunResponse(
            id=document.id, pipeline_id=document.pipeline_id, input=document.input,
            status=document.status,
            current_activity_run=activity_run_response(child) if child is not None else None,
            steps=[
                PipelineRunStepResponse(
                    activity_id=step.activity_id, status=step.status,
                    activity_run_id=step.activity_run_id,
                )
                for step in document.steps
            ],
            created_at=document.created_at, created_by=document.created_by,
            updated_at=document.updated_at,
        )
