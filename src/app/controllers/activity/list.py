"""Controller for listing activity definitions."""

from src.app.schemas.activity import ActivityListResponse, ActivityResponse
from src.app.services.activities.service import ActivityService


class ActivityListController:
    """Return one page of activity definitions."""

    async def list(
        self,
        *,
        user_id: str,
        offset: int,
        requested_workspace_id: str | None = None,
    ) -> ActivityListResponse:
        """Return one activity page."""
        documents, total = await self._activity_service.list(
            user_id=user_id,
            offset=offset,
            requested_workspace_id=requested_workspace_id,
        )
        return ActivityListResponse(
            items=[ActivityResponse.model_validate(item) for item in documents],
            total=total,
        )

    _activity_service: ActivityService