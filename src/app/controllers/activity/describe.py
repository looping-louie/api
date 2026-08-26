"""Controller for describing activity definitions."""

from src.app.schemas.activity import ActivityResponse
from src.app.services.activities.service import ActivityService


class ActivityDescribeController:
    """Return one activity definition."""

    async def get(
        self,
        *,
        user_id: str,
        activity_id: str,
    ) -> ActivityResponse:
        """Return one activity."""
        document = await self._activity_service.get(
            user_id=user_id,
            activity_id=activity_id,
        )
        return ActivityResponse.model_validate(document)

    _activity_service: ActivityService
