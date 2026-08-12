"""Controller for creating loop runs."""

from src.app.schemas.loop_run import LoopRunCreateRequest, LoopRunResponse
from src.app.services.loop_runs import LoopRunService

from .utils import loop_run_response


class LoopRunCreateController:
    """Create loop runs from loops or activities."""

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
        return loop_run_response(document)

    async def create_for_activity(
        self,
        *,
        user_id: str,
        activity_id: str,
        payload: LoopRunCreateRequest,
        requested_workspace_id: str | None = None,
    ) -> LoopRunResponse:
        """Create one run from an activity loop configuration."""
        document = await self._loop_run_service.create_for_activity(
            user_id=user_id,
            activity_id=activity_id,
            input_text=payload.input,
            requested_workspace_id=requested_workspace_id,
        )
        return loop_run_response(document)

    _loop_run_service: LoopRunService