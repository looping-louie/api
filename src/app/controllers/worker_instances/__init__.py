"""Controllers for global Worker HTTP operations."""

from src.app.services.worker_instances import WorkerInstanceService

from .create import WorkerInstanceCreateController
from .enable_project import WorkerInstanceEnableProjectController
from .heartbeat import WorkerInstanceHeartbeatController


class WorkerInstanceController(
    WorkerInstanceCreateController,
    WorkerInstanceEnableProjectController,
    WorkerInstanceHeartbeatController,
):
    """Compose endpoint-specific global Worker controllers."""

    def __init__(self, *, service: WorkerInstanceService) -> None:
        """Store the global Worker lifecycle service."""

        self._worker_instance_service = service


__all__ = [
    'WorkerInstanceController',
    'WorkerInstanceCreateController',
    'WorkerInstanceEnableProjectController',
    'WorkerInstanceHeartbeatController',
]