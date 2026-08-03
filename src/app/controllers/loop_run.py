"""HTTP controller for loop-run creation and lookup."""

from src.app.schemas.loop_run import (
    LoopRunCreateRequest,
    LoopRunContinueRequest,
    LoopRunListResponse,
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
        return LoopRunResponse.model_validate(document)

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
        return LoopRunResponse.model_validate(document)

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

        document = await self._loop_run_service.continue_collect_snapshot(
            user_id=user_id,
            loop_id=loop_id,
            run_id=run_id,
            continuation_token=payload.continuation_token,
            idempotency_key=payload.idempotency_key,
            repo_context=payload.result.repo_context,
            workspace_path=payload.result.workspace_metadata.workspace_path,
            source_commit_sha=(
                payload.result.workspace_metadata.source_commit_sha
            ),
            constitution=payload.result.constitution,
            project_profile=payload.result.project_profile.model_dump(
                mode='json',
            ),
            requested_workspace_id=requested_workspace_id,
        )
        return LoopRunResponse.model_validate(document)

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
            items=[LoopRunResponse.model_validate(item) for item in documents],
            total=total,
        )