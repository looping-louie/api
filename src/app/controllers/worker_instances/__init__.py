"""Controllers for Worker HTTP operations."""

from collections.abc import Callable
from datetime import datetime

from src.app.repositories.pipeline_runs.repository import PipelineRunRepository
from src.app.services.worker_instances import WorkerInstanceService

from .create import WorkerInstanceCreateController
from .describe import WorkerInstanceDescribeController
from .disable_project import WorkerInstanceDisableProjectController
from .enable_project import WorkerInstanceEnableProjectController
from .heartbeat import WorkerInstanceHeartbeatController
from .list import WorkerInstanceListController


class WorkerInstanceController(
    WorkerInstanceCreateController,
    WorkerInstanceDescribeController,
    WorkerInstanceDisableProjectController,
    WorkerInstanceEnableProjectController,
    WorkerInstanceHeartbeatController,
    WorkerInstanceListController,
):
    """Compose endpoint-specific Worker controllers."""

    def __init__(
        self,
        *,
        service: WorkerInstanceService,
        pipeline_run_repository: PipelineRunRepository,
        clock: Callable[[], datetime],
    ) -> None:
        """Store the Worker lifecycle service."""

        WorkerInstanceListController.__init__(
            self,
            service=service,
            pipeline_run_repository=pipeline_run_repository,
            clock=clock,
        )


__all__ = [
    'WorkerInstanceController',
    'WorkerInstanceCreateController',
    'WorkerInstanceDescribeController',
    'WorkerInstanceDisableProjectController',
    'WorkerInstanceEnableProjectController',
    'WorkerInstanceHeartbeatController',
    'WorkerInstanceListController',
]
