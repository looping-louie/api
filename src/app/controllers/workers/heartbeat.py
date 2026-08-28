"""Controller for recording Worker heartbeats."""

from src.app.schemas.worker import WorkerResponse
from src.app.services.workers import WorkerService

from .response import worker_response


class WorkerHeartbeatController:
    """Refresh registered Worker liveness."""

    async def heartbeat(
        self,
        *,
        user_id: str,
        worker_id: str,
        requested_project_id: str | None = None,
    ) -> WorkerResponse:
        """Record one liveness heartbeat for a registered Worker."""

        return worker_response(await self._worker_service.heartbeat(
            user_id=user_id,
            worker_id=worker_id,
            requested_project_id=requested_project_id,
        ))

    _worker_service: WorkerService