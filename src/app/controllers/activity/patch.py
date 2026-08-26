"""Controller for patching activity definitions."""

from src.app.schemas.activity import ActivityPatchRequest, ActivityResponse
from src.app.services.activities.service import ActivityService

from .utils import activity_changes


class ActivityPatchController:
    """Apply supplied fields to one activity definition."""

    async def patch(
        self,
        *,
        user_id: str,
        activity_id: str,
        payload: ActivityPatchRequest,
    ) -> ActivityResponse:
        """Apply supplied activity fields."""
        document = await self._activity_service.patch(
            user_id=user_id,
            activity_id=activity_id,
            changes=activity_changes(payload),
        )
        return ActivityResponse.model_validate(document)

    _activity_service: ActivityService
