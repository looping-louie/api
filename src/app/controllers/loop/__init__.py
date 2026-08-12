"""Controllers for loop HTTP operations."""

from src.app.services.loops.service import LoopService

from .create import LoopCreateController
from .delete import LoopDeleteController
from .describe import LoopDescribeController
from .list import LoopListController
from .list_changelog import LoopListChangelogController
from .patch import LoopPatchController


class LoopController(
    LoopListController,
    LoopDescribeController,
    LoopCreateController,
    LoopPatchController,
    LoopDeleteController,
    LoopListChangelogController,
):
    """Compatibility composition of the endpoint-specific controllers."""

    def __init__(self, *, loop_service: LoopService) -> None:
        """Store the shared loop application service."""
        self._loop_service = loop_service


__all__ = [
    "LoopController",
    "LoopCreateController",
    "LoopDeleteController",
    "LoopDescribeController",
    "LoopListChangelogController",
    "LoopListController",
    "LoopPatchController",
]
