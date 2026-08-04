"""HTTP controller for loop-run creation and lookup."""

from src.app.schemas.loop_run import (
    LoopRunApplyOperationsResult,
    LoopRunCommitResult,
    LoopRunCollectSnapshotResult,
    LoopRunCreateRequest,
    LoopRunContinueRequest,
    LoopRunListResponse,
    LoopRunReviewInputResult,
    LoopRunResponse,
)
from src.app.services.loop_runs.service import LoopRunService


class LoopRunController:
    """Translate loop-run application results into HTTP schemas."""

    def __init__(self, *, loop_run_service: LoopRunService) -> None:
        """Store the loop-run application service."""

        self._loop_run_service = loop_run_service

    async def create(
        self,
        *,
        user_id: str,
        loop_id: str,
        payload: LoopRunCreateRequest,
        requested_workspace_id: str | None = None,
    ) -> LoopRunResponse:
        """Create one loop run awaiting its first CLI checkpoint."""

        document = await self._loop_run_service.create(
            user_id=user_id,
            loop_id=loop_id,
            input_text=payload.input,
            requested_workspace_id=requested_workspace_id,
        )
        return self._response(document)

    async def get(
        self,
        *,
        user_id: str,
        loop_id: str,
        run_id: str,
        requested_workspace_id: str | None = None,
    ) -> LoopRunResponse:
        """Return one loop run under its parent loop."""

        document = await self._loop_run_service.get(
            user_id=user_id,
            loop_id=loop_id,
            run_id=run_id,
            requested_workspace_id=requested_workspace_id,
        )
        return self._response(document)

    async def continue_collect_snapshot(
        self,
        *,
        user_id: str,
        loop_id: str,
        run_id: str,
        payload: LoopRunContinueRequest,
        requested_workspace_id: str | None = None,
    ) -> LoopRunResponse:
        """Record the CLI snapshot required before generation can begin."""

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
            result = self._action_result(payload.result)
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
        return self._response(document)

    @staticmethod
    def _action_result(payload: dict[str, object]) -> LoopRunApplyOperationsResult | LoopRunReviewInputResult | LoopRunCommitResult:
        """Validate a non-snapshot CLI action using its action discriminator."""

        action = payload.get('action')
        schemas = {
            'apply_operations': LoopRunApplyOperationsResult,
            'submit_review_input': LoopRunReviewInputResult,
            'commit_if_allowed': LoopRunCommitResult,
        }
        schema = schemas.get(action)
        if schema is None:
            raise ValueError('result.action is not supported')
        return schema.model_validate(payload)

    @staticmethod
    def _response(document: object) -> LoopRunResponse:
        """Expose persisted CLI runtime artifacts without leaking full context."""

        response = LoopRunResponse.model_validate(document)
        context = getattr(document, 'execution_context', {})
        artifacts = (
            context.get('runtime_artifacts', {})
            if isinstance(context, dict)
            else {}
        )
        return response.model_copy(update={'payload': artifacts})

    async def list(
        self,
        *,
        user_id: str,
        loop_id: str,
        offset: int,
        requested_workspace_id: str | None = None,
    ) -> LoopRunListResponse:
        """Return one page of loop runs under their parent loop."""

        documents, total = await self._loop_run_service.list(
            user_id=user_id,
            loop_id=loop_id,
            offset=offset,
            requested_workspace_id=requested_workspace_id,
        )
        return LoopRunListResponse(
            items=[self._response(item) for item in documents],
            total=total,
        )
