"""Read global Workers enabled for one Project."""

from collections.abc import Callable
from datetime import datetime

from src.app.schemas.worker import WorkerInstanceProjectResponse
from src.app.services.worker_instances import WorkerInstanceService

from .response import worker_instance_project_response


class WorkerInstanceListController:
    """Expose Project-scoped global Worker operational state."""

    def __init__(
        self,
        *,
        service: WorkerInstanceService,
        clock: Callable[[], datetime],
    ) -> None:
        """Store Worker lookup dependencies."""

        self._worker_instance_service = service
        self._clock = clock

    async def list_for_project(
        self,
        *,
        user_id: str,
        project_id: str | None,
    ) -> list[WorkerInstanceProjectResponse]:
        """Return global Workers enabled for the requested Project."""

        workers = await self._worker_instance_service.list_for_project(
            user_id=user_id,
            requested_project_id=project_id,
        )
        observed_at = self._clock()
        return [
            worker_instance_project_response(worker, observed_at=observed_at)
            for worker in workers
        ]

    _worker_instance_service: WorkerInstanceService
    _clock: Callable[[], datetime]