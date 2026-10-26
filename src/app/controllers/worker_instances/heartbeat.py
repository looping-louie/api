"""Controller for recording Worker heartbeats."""

from src.app.models.worker import WorkerHarnessCapability
from src.app.schemas.worker import WorkerHeartbeatRequest, WorkerResponse
from src.app.services.worker_instances import WorkerInstanceService

from .response import worker_instance_response


class WorkerInstanceHeartbeatController:
    """Refresh Worker liveness and reported Harness capabilities."""

    async def heartbeat(
        self,
        *,
        user_id: str,
        worker_id: str,
        payload: WorkerHeartbeatRequest,
    ) -> WorkerResponse:
        """Record one liveness heartbeat for a registered Worker."""

        return worker_instance_response(
            await self._worker_instance_service.heartbeat(
                user_id=user_id,
                worker_instance_id=worker_id,
                harnesses=tuple(
                    WorkerHarnessCapability(
                        kind=harness.kind,
                        version=harness.version,
                        config=dict(harness.config),
                    )
                    for harness in payload.harnesses
                ),
            ),
        )

    _worker_instance_service: WorkerInstanceService
