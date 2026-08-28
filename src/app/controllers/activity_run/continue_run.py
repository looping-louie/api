"""Controller for continuing Activity Runs."""

from src.app.schemas.activity_run import (
    ActivityRunCollectSnapshotResult,
    ActivityRunContinueRequest,
    ActivityRunHarnessResult,
    ActivityRunHumanDecisionResult,
    ActivityRunResponse,
)
from src.app.services.activity_runs import ActivityRunService

from .utils import action_result, activity_run_response


class ActivityRunContinueController:
    """Advance Activity-owned execution checkpoints."""

    async def continue_run(
        self,
        *,
        user_id: str,
        activity_id: str,
        run_id: str,
        payload: ActivityRunContinueRequest,
        requested_project_id: str | None = None,
    ) -> ActivityRunResponse:
        """Advance one Activity-owned execution checkpoint."""

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
            else ActivityRunHarnessResult.model_validate(payload.result).model_dump(mode='json')
            if action == 'run_harness'
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
            requested_project_id=requested_project_id,
        )
        return activity_run_response(document)

    _activity_run_service: ActivityRunService