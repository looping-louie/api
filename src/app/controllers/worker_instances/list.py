"""Read global Workers enabled for one Project."""

from collections.abc import Callable
from datetime import datetime

from src.app.repositories.pipeline_runs.repository import PipelineRunRepository
from src.app.schemas.worker import WorkerInstanceProjectResponse
from src.app.services.worker_instances import (
    GLOBAL_WORKER_ACTIVE_CLAIM_LIMIT,
    WorkerInstanceService,
)

from .response import worker_instance_project_response


class WorkerInstanceListController:
    """Expose Project-scoped global Worker operational state."""

    def __init__(
        self,
        *,
        service: WorkerInstanceService,
        pipeline_run_repository: PipelineRunRepository,
        clock: Callable[[], datetime],
    ) -> None:
        """Store Worker lookup dependencies."""

        self._worker_instance_service = service
        self._pipeline_run_repository = pipeline_run_repository
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
        active_claim_counts = await self._pipeline_run_repository.active_claim_counts(
            worker_ids=tuple(worker.worker.id for worker in workers),
            observed_at=observed_at,
        )
        return [
            worker_instance_project_response(
                worker,
                observed_at=observed_at,
                active_claims=active_claim_counts.get(worker.worker.id, 0),
                capacity=GLOBAL_WORKER_ACTIVE_CLAIM_LIMIT,
            )
            for worker in workers
        ]

    _worker_instance_service: WorkerInstanceService
    _pipeline_run_repository: PipelineRunRepository
    _clock: Callable[[], datetime]