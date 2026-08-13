"""Controller for listing loop runs."""

from src.app.schemas.loop_run import LoopRunListResponse
from src.app.services.loop_runs import LoopRunService

from .utils import loop_run_response


class LoopRunListController:
    """Return loop-run pages from loops or activities."""

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
            items=[loop_run_response(item) for item in documents],
            total=total,
        )

    async def list_for_activity(
        self,
        *,
        user_id: str,
        activity_id: str,
        offset: int,
        requested_workspace_id: str | None = None,
    ) -> LoopRunListResponse:
        """Return one activity-owned run page."""
        documents, total = await self._loop_run_service.list_for_activity(
            user_id=user_id,
            activity_id=activity_id,
            offset=offset,
            requested_workspace_id=requested_workspace_id,
        )
        return LoopRunListResponse(
            items=[loop_run_response(item) for item in documents],
            total=total,
        )

    _loop_run_service: LoopRunService
