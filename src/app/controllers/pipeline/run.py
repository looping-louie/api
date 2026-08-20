"""Controllers for dependency-aware pipeline execution."""

from datetime import timedelta

from src.app.controllers.activity_runs.utils import activity_run_response
from src.app.models.activity_run import ActivityRunDocument
from src.app.models.pipeline_run import PipelineRunDocument
from src.app.schemas.pipeline import (
    PipelineRunClaimRequest,
    PipelineRunClaimResponse,
    PipelineRunClaimableListResponse,
    PipelineRunClaimableResponse,
    PipelineRunContinueRequest,
    PipelineRunCreateRequest,
    PipelineRunEventListResponse,
    PipelineRunEventResponse,
    PipelineRunLeaseResponse,
    PipelineRunResponse,
    PipelineRunStepResponse,
)
from src.app.services.pipeline_runs import PipelineRunService
from src.app.services.pipeline_runs.etag import pipeline_run_etag


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
            commit_mode=payload.commit_mode,
            requested_workspace_id=requested_workspace_id,
        )
        return self._response(document, child)

    async def list_claimable_runs(
        self, *, user_id: str, pipeline_id: str,
        requested_workspace_id: str | None = None,
    ) -> PipelineRunClaimableListResponse:
        """Return current claimable runs beneath one active Pipeline."""

        documents = await self._require_service().list_claimable(
            user_id=user_id, pipeline_id=pipeline_id,
            requested_workspace_id=requested_workspace_id,
        )
        return PipelineRunClaimableListResponse(
            items=[
                PipelineRunClaimableResponse(
                    run=self._response(document, None),
                    etag=pipeline_run_etag(document),
                )
                for document in documents
            ],
            total=len(documents),
        )

    async def claim_run(
        self, *, user_id: str, pipeline_id: str, run_id: str,
        payload: PipelineRunClaimRequest, if_match: str,
        requested_workspace_id: str | None = None,
    ) -> PipelineRunClaimResponse:
        """Claim one Pipeline run when the supplied entity tag is current."""

        document, child, lease_token = await self._require_service().claim(
            user_id=user_id, pipeline_id=pipeline_id, run_id=run_id,
            worker_id=payload.worker_id, if_match=if_match,
            lease_duration=timedelta(minutes=1),
            requested_workspace_id=requested_workspace_id,
        )
        return PipelineRunClaimResponse(
            run=self._response(document, child), lease_token=lease_token,
        )

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

    async def renew_lease(
        self, *, user_id: str, pipeline_id: str, run_id: str,
        lease_token: str, requested_workspace_id: str | None = None,
    ) -> PipelineRunLeaseResponse:
        """Extend the active worker lease for one Pipeline run by one minute."""

        document = await self._require_service().renew_lease(
            user_id=user_id, pipeline_id=pipeline_id, run_id=run_id,
            lease_token=lease_token, lease_duration=timedelta(minutes=1),
            requested_workspace_id=requested_workspace_id,
        )
        if document.lease_expires_at is None:
            raise RuntimeError('Renewed Pipeline run is missing lease expiration.')
        return PipelineRunLeaseResponse(lease_expires_at=document.lease_expires_at)

    async def continue_run(
        self, *, user_id: str, pipeline_id: str, run_id: str,
        payload: PipelineRunContinueRequest,
        requested_workspace_id: str | None = None,
    ) -> PipelineRunResponse:
        """Schedule after the current child activity run reaches a terminal state."""

        document, child = await self._require_service().continue_run(
            user_id=user_id, pipeline_id=pipeline_id, run_id=run_id,
            lease_token=payload.lease_token,
            requested_workspace_id=requested_workspace_id,
        )
        return self._response(document, child)

    async def list_events(
        self, *, user_id: str, pipeline_id: str, run_id: str,
        requested_workspace_id: str | None = None,
    ) -> PipelineRunEventListResponse:
        """Return the immutable event ledger for one Pipeline run."""

        document, _ = await self._require_service().get(
            user_id=user_id, pipeline_id=pipeline_id, run_id=run_id,
            requested_workspace_id=requested_workspace_id,
        )
        return PipelineRunEventListResponse(
            items=[
                PipelineRunEventResponse(
                    id=event.id, event_type=event.event_type,
                    activity_id=event.activity_id, actor_id=event.actor_id,
                    payload=dict(event.payload), created_at=event.created_at,
                )
                for event in document.events
            ],
            total=len(document.events),
        )

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
            commit_mode=document.commit_mode,
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
