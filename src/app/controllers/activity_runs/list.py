"""Controller for listing Activity Runs."""

from src.app.schemas.activity_run import ActivityRunListResponse
from src.app.services.activity_runs import ActivityRunService

from .utils import activity_run_response


class ActivityRunListController:
    """List executions owned by an Activity."""

    async def list(
        self,
        *,
        user_id: str,
        activity_id: str,
        offset: int,
        requested_project_id: str | None = None,
    ) -> ActivityRunListResponse:
        """Return one page of Activity-owned executions."""

        documents, total = await self._activity_run_service.list(
            user_id=user_id,
            activity_id=activity_id,
            offset=offset,
            requested_project_id=requested_project_id,
        )
        return ActivityRunListResponse(
            items=[activity_run_response(document) for document in documents],
            total=total,
        )

    _activity_run_service: ActivityRunService