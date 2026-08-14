"""Controller for advancing loop-run checkpoints."""

from src.app.schemas.loop_run import (
    LoopRunCollectSnapshotResult,
    LoopRunContinueRequest,
    LoopRunResponse,
)
from src.app.services.loop_runs import LoopRunService

from .utils import action_result, loop_run_response


class LoopRunAdvanceController:
    """Advance loop-run checkpoints from loop definitions."""

    async def continue_collect_snapshot(
        self,
        *,
        user_id: str,
        loop_id: str,
        run_id: str,
        payload: LoopRunContinueRequest,
        requested_workspace_id: str | None = None,
    ) -> LoopRunResponse:
        """Record a CLI snapshot or subsequent checkpoint result."""
        action = payload.result.get('action')
        if action == 'collect_snapshot':
            result = LoopRunCollectSnapshotResult.model_validate(payload.result)
            document = await self._loop_run_service.continue_collect_snapshot(
                user_id=user_id,
                loop_id=loop_id,
                run_id=run_id,
                continuation_token=payload.continuation_token,
                idempotency_key=payload.idempotency_key,
                repo_context=result.repo_context,
                workspace_path=result.workspace_metadata.workspace_path,
                source_commit_sha=result.workspace_metadata.source_commit_sha,
                constitution=result.constitution,
                project_profile=result.project_profile.model_dump(mode='json'),
                requested_workspace_id=requested_workspace_id,
            )
        else:
            result = action_result(payload.result)
            document = await self._loop_run_service.continue_action(
                user_id=user_id,
                loop_id=loop_id,
                run_id=run_id,
                continuation_token=payload.continuation_token,
                idempotency_key=payload.idempotency_key,
                action=result.action,
                result=result.model_dump(mode='json'),
                requested_workspace_id=requested_workspace_id,
            )
        return loop_run_response(document)

    _loop_run_service: LoopRunService
