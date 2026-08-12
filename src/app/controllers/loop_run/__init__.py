"""Controllers for loop-run HTTP operations."""

from src.app.services.loop_runs import LoopRunService

from .advance import LoopRunAdvanceController
from .create import LoopRunCreateController
from .describe import LoopRunDescribeController
from .list import LoopRunListController


class LoopRunController(
    LoopRunListController,
    LoopRunDescribeController,
    LoopRunCreateController,
    LoopRunAdvanceController,
):
    """Compatibility composition of the endpoint-specific controllers."""

    def __init__(self, *, loop_run_service: LoopRunService) -> None:
        """Store the loop-run application service."""
        self._loop_run_service = loop_run_service


__all__ = [
    'LoopRunAdvanceController',
    'LoopRunController',
    'LoopRunCreateController',
    'LoopRunDescribeController',
    'LoopRunListController',
]
