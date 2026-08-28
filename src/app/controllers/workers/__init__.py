"""Controllers for Worker HTTP operations."""

from src.app.services.workers import WorkerService

from .create import WorkerCreateController
from .heartbeat import WorkerHeartbeatController


class WorkerController(
    WorkerCreateController,
    WorkerHeartbeatController,
):
    """Compose endpoint-specific Worker controllers."""

    def __init__(self, *, worker_service: WorkerService) -> None:
        """Store the Worker registration application service."""

        self._worker_service = worker_service


__all__ = [
    'WorkerController',
    'WorkerCreateController',
    'WorkerHeartbeatController',
]
