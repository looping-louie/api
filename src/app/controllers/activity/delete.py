"""Controller for deleting activity definitions."""

from src.app.schemas.shared import DeleteResponse
from src.app.services.activities.service import ActivityService


class ActivityDeleteController:
    """Delete one activity definition."""

    async def delete(
        self,
        *,
        user_id: str,
        activity_id: str,
        requested_workspace_id: str | None = None,
    ) -> DeleteResponse:
        """Delete one activity."""
        await self._activity_service.delete(
            user_id=user_id,
            activity_id=activity_id,
            requested_workspace_id=requested_workspace_id,
        )
        return DeleteResponse()

    _activity_service: ActivityService