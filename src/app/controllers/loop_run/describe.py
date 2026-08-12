"""Controller for describing loop runs."""

from src.app.schemas.loop_run import LoopRunResponse
from src.app.services.loop_runs import LoopRunService

from .utils import loop_run_response


class LoopRunDescribeController:
    """Return loop runs from loops or activities."""

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
        return loop_run_response(document)

    async def get_for_activity(
        self,
        *,
        user_id: str,
        activity_id: str,
        run_id: str,
        requested_workspace_id: str | None = None,
    ) -> LoopRunResponse:
        """Return one activity-owned run."""
        document = await self._loop_run_service.get_for_activity(
            user_id=user_id,
            activity_id=activity_id,
            run_id=run_id,
            requested_workspace_id=requested_workspace_id,
        )
        return loop_run_response(document)

    _loop_run_service: LoopRunService