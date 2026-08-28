"""Controllers for Activity Run HTTP operations."""

from src.app.services.activity_runs import ActivityRunService

from .continue_run import ActivityRunContinueController
from .describe import ActivityRunDescribeController
from .list import ActivityRunListController


class ActivityRunController(
    ActivityRunContinueController,
    ActivityRunDescribeController,
    ActivityRunListController,
):
    """Compose endpoint-specific Activity Run controllers."""

    def __init__(self, *, activity_run_service: ActivityRunService) -> None:
        """Store the Activity Run application service."""

        self._activity_run_service = activity_run_service


__all__ = [
    'ActivityRunContinueController',
    'ActivityRunController',
    'ActivityRunDescribeController',
    'ActivityRunListController',
]
