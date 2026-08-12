"""Controllers for activity HTTP operations."""

from src.app.services.activities.service import ActivityService

from .create import ActivityCreateController
from .delete import ActivityDeleteController
from .describe import ActivityDescribeController
from .list import ActivityListController
from .list_changelog import ActivityListChangelogController
from .patch import ActivityPatchController


class ActivityController(
    ActivityListController,
    ActivityDescribeController,
    ActivityCreateController,
    ActivityPatchController,
    ActivityDeleteController,
    ActivityListChangelogController,
):
    """Compatibility composition of the endpoint-specific controllers."""

    def __init__(self, *, activity_service: ActivityService) -> None:
        """Store the shared activity application service."""
        self._activity_service = activity_service


__all__ = [
    'ActivityController',
    'ActivityCreateController',
    'ActivityDeleteController',
    'ActivityDescribeController',
    'ActivityListChangelogController',
    'ActivityListController',
    'ActivityPatchController',
]