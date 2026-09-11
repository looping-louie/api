"""Controller for listing activity changelog entries."""

from src.app.schemas.activity import (
    ActivityChangelogEntryResponse,
    ActivityChangelogListResponse,
)
from src.app.services.activities.service import ActivityService


class ActivityListChangelogController:
    """Return one page of activity changelog entries."""

    async def list_changelog(
        self,
        *,
        user_id: str,
        activity_id: str,
        offset: int,
    ) -> ActivityChangelogListResponse:
        """Return one activity changelog page."""
        entries, total = await self._activity_service.list_changelog(
            user_id=user_id,
            activity_id=activity_id,
            offset=offset,
        )
        return ActivityChangelogListResponse(
            items=[
                ActivityChangelogEntryResponse.model_validate(entry)
                for entry in entries
            ],
            total=total,
        )

    _activity_service: ActivityService
