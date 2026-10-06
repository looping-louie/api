"""Controller for registering globally identified Workers."""

from src.app.models.worker import WorkerHarnessCapability
from src.app.schemas.worker import WorkerInstanceCreateRequest, WorkerResponse
from src.app.services.worker_instances import WorkerInstanceService

from .response import worker_instance_response


class WorkerInstanceCreateController:
    """Register global Workers with authorized initial Project assignments."""

    async def create(
        self,
        *,
        user_id: str,
        payload: WorkerInstanceCreateRequest,
    ) -> WorkerResponse:
        """Register one global Worker and enable its initial Project."""

        return worker_instance_response(await self._worker_instance_service.register(
            user_id=user_id,
            project_id=payload.project_id,
            harnesses=tuple(
                WorkerHarnessCapability(
                    kind=harness.kind,
                    version=harness.version,
                    config=dict(harness.config),
                )
                for harness in payload.harnesses
            ),
        ))

    _worker_instance_service: WorkerInstanceService
