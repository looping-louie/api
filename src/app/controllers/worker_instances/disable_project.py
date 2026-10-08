"""Controller for disabling Workers from Project work."""

from src.app.schemas.shared import DeleteResponse
from src.app.services.worker_instances import WorkerInstanceService


class WorkerInstanceDisableProjectController:
    """Disable Worker execution authorization for accessible Projects."""

    async def disable_project(
        self,
        *,
        user_id: str,
        worker_id: str,
        project_id: str,
    ) -> DeleteResponse:
        """Prevent one Worker from claiming future work for one Project."""

        await self._worker_instance_service.disable_project(
            user_id=user_id,
            worker_instance_id=worker_id,
            project_id=project_id,
        )
        return DeleteResponse()

    _worker_instance_service: WorkerInstanceService