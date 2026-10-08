"""Controller for describing one Worker."""

from src.app.schemas.worker import WorkerResponse
from src.app.services.worker_instances import WorkerInstanceService

from .response import worker_instance_response


class WorkerInstanceDescribeController:
    """Expose Worker identity without Project enablement state."""

    async def describe(
        self,
        *,
        user_id: str,
        worker_instance_id: str,
    ) -> WorkerResponse:
        """Return one Worker owned by the requesting User."""

        return worker_instance_response(
            await self._worker_instance_service.get_for_user(
                user_id=user_id,
                worker_instance_id=worker_instance_id,
            ),
        )

    _worker_instance_service: WorkerInstanceService
