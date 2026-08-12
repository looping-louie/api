"""Controllers for pipeline HTTP operations."""

from src.app.services.pipelines.service import PipelineService

from .create import PipelineCreateController
from .delete import PipelineDeleteController
from .describe import PipelineDescribeController
from .list import PipelineListController
from .list_changelog import PipelineListChangelogController
from .patch import PipelinePatchController


class PipelineController(
    PipelineListController,
    PipelineDescribeController,
    PipelineCreateController,
    PipelinePatchController,
    PipelineDeleteController,
    PipelineListChangelogController,
):
    """Compatibility composition of the endpoint-specific controllers."""

    def __init__(self, *, pipeline_service: PipelineService) -> None:
        """Store the shared pipeline application service."""
        self._pipeline_service = pipeline_service


__all__ = [
    "PipelineController",
    "PipelineCreateController",
    "PipelineDeleteController",
    "PipelineDescribeController",
    "PipelineListChangelogController",
    "PipelineListController",
    "PipelinePatchController",
]
