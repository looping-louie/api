"""HTTP controller for activity-owned execution checkpoints."""

from src.app.schemas.activity_run import (
    ActivityRunListResponse,
    ActivityRunResponse,
    ActivityRunCollectSnapshotResult,
    ActivityRunContinueRequest,
    ActivityRunCreateRequest,
    ActivityRunHumanDecisionResult,
)
from src.app.services.activity_runs import ActivityRunService

from .activity_runs.utils import action_result, activity_run_response


class ActivityRunController:
    """Translate activity-run HTTP contracts into application service calls."""

    def __init__(self, *, activity_run_service: ActivityRunService) -> None:
        """Store the activity-run application service."""

        self._activity_run_service = activity_run_service

    async def create(
        self,
        *,
        user_id: str,
        activity_id: str,
        payload: ActivityRunCreateRequest,
        requested_workspace_id: str | None = None,
    ) -> ActivityRunResponse:
        """Create one activity-owned execution."""

        document = await self._activity_run_service.create(
            user_id=user_id,
            activity_id=activity_id,
            input_text=payload.input,
            requested_workspace_id=requested_workspace_id,
        )
        return activity_run_response(document)

    async def get(
        self,
        *,
        user_id: str,
        activity_id: str,
        run_id: str,
        requested_workspace_id: str | None = None,
    ) -> ActivityRunResponse:
        """Return one activity-owned execution."""

        document = await self._activity_run_service.get(
            user_id=user_id,
            activity_id=activity_id,
            run_id=run_id,
            requested_workspace_id=requested_workspace_id,
        )
        return activity_run_response(document)

    async def list(
        self,
        *,
        user_id: str,
        activity_id: str,
        offset: int,
        requested_workspace_id: str | None = None,
    ) -> ActivityRunListResponse:
        """Return one page of activity-owned executions."""

        documents, total = await self._activity_run_service.list(
            user_id=user_id,
            activity_id=activity_id,
            offset=offset,
            requested_workspace_id=requested_workspace_id,
        )
        return ActivityRunListResponse(
            items=[activity_run_response(document) for document in documents],
            total=total,
        )

    async def continue_run(
        self,
        *,
        user_id: str,
        activity_id: str,
        run_id: str,
        payload: ActivityRunContinueRequest,
        requested_workspace_id: str | None = None,
    ) -> ActivityRunResponse:
        """Advance one activity-owned CLI checkpoint."""

        action = payload.result.get('action')
        result = (
            ActivityRunCollectSnapshotResult.model_validate(
                payload.result
            ).model_dump(
                mode='json'
            )
            if action == 'collect_snapshot'
            else ActivityRunHumanDecisionResult.model_validate(
                payload.result
            ).model_dump(mode='json')
            if action == 'submit_human_decision'
            else action_result(payload.result).model_dump(mode='json')
        )
        document = await self._activity_run_service.continue_run(
            user_id=user_id,
            activity_id=activity_id,
            run_id=run_id,
            pipeline_run_id=payload.pipeline_run_id,
            lease_token=payload.lease_token,
            continuation_token=payload.continuation_token,
            idempotency_key=payload.idempotency_key,
            action=str(action),
            result=result,
            requested_workspace_id=requested_workspace_id,
        )
        return activity_run_response(document)
