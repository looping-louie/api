"""Controller for describing Activity Runs."""

from src.app.schemas.activity_run import ActivityRunResponse
from src.app.services.activity_runs import ActivityRunService

from .utils import activity_run_response


class ActivityRunDescribeController:
    """Retrieve one Activity-owned execution."""

    async def get(
        self,
        *,
        user_id: str,
        activity_id: str,
        run_id: str,
        requested_project_id: str | None = None,
    ) -> ActivityRunResponse:
        """Return one Activity-owned execution."""

        document = await self._activity_run_service.get(
            user_id=user_id,
            activity_id=activity_id,
            run_id=run_id,
            requested_project_id=requested_project_id,
        )
        return activity_run_response(document)

    _activity_run_service: ActivityRunService