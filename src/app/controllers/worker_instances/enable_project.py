"""Controller for enabling global Workers to execute Project work."""

from src.app.schemas.worker import WorkerProjectEnablementResponse
from src.app.services.worker_instances import WorkerInstanceService

from .response import worker_project_enablement_response


class WorkerInstanceEnableProjectController:
    """Enable global Workers for Projects accessible to the request User."""

    async def enable_project(
        self,
        *,
        user_id: str,
        worker_id: str,
        project_id: str,
    ) -> WorkerProjectEnablementResponse:
        """Enable one global Worker to claim work for one Project."""

        return worker_project_enablement_response(
            await self._worker_instance_service.enable_project(
                user_id=user_id,
                worker_instance_id=worker_id,
                project_id=project_id,
            ),
        )

    _worker_instance_service: WorkerInstanceService