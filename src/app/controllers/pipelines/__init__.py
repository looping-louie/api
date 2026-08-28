"""Controllers for pipeline HTTP operations."""

from src.app.services.pipelines.service import PipelineService
from src.app.services.pipeline_runs import PipelineRunService

from .create import PipelineCreateController
from .delete import PipelineDeleteController
from .describe import PipelineDescribeController
from .list import PipelineListController
from .list_changelog import PipelineListChangelogController
from .patch import PipelinePatchController
from .run import PipelineRunController


class PipelineController(
    PipelineListController,
    PipelineDescribeController,
    PipelineCreateController,
    PipelinePatchController,
    PipelineDeleteController,
    PipelineListChangelogController,
    PipelineRunController,
):
    """Compatibility composition of the endpoint-specific controllers."""

    def __init__(
        self,
        *,
        pipeline_service: PipelineService,
        pipeline_run_service: PipelineRunService | None = None,
    ) -> None:
        """Store the shared pipeline application service."""
        self._pipeline_service = pipeline_service
        self._pipeline_run_service = pipeline_run_service


__all__ = [
    "PipelineController",
    "PipelineCreateController",
    "PipelineDeleteController",
    "PipelineDescribeController",
    "PipelineListChangelogController",
    "PipelineListController",
    "PipelinePatchController",
    "PipelineRunController",
]
