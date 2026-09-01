"""Read models for queued Pipeline worker readiness."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Mapping

from src.app.models.pipeline_run import PipelineRunDocument
from src.app.repositories.pipeline_runs.repository import PipelineRunRepository
from src.app.services.pipeline_runs.graph import snapshot_dependencies
from src.app.services.pipeline_runs.snapshot import harness_snapshot
from src.app.services.pipeline_runs.types import PipelineRunNotFoundError
from src.app.services.shared.tenant import TenantService
from src.app.services.workers import WorkerService


PipelineRunReadinessStatus = Literal[
    'not_applicable',
    'no_registered_workers',
    'no_active_workers',
    'no_compatible_workers',
    'ready',
]


@dataclass(frozen=True, slots=True)
class PipelineRunReadiness:
    """Aggregated worker availability for one queued Pipeline run."""

    status: PipelineRunReadinessStatus
    project_id: str
    required_harness: Mapping[str, object] | None
    registered_worker_count: int
    active_worker_count: int
    compatible_worker_count: int
    latest_heartbeat_at: datetime | None
    observed_at: datetime


class PipelineRunReadinessService:
    """Resolve queued-run Harness requirements against active Workers."""

    def __init__(
        self,
        *,
        repository: PipelineRunRepository,
        tenant_service: TenantService,
        worker_service: WorkerService | None,
        clock: Callable[[], datetime],
    ) -> None:
        """Store run persistence, tenancy, worker, and time dependencies."""

        self._repository = repository
        self._tenant_service = tenant_service
        self._worker_service = worker_service
        self._clock = clock

    async def get(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        run_id: str,
        requested_project_id: str | None = None,
    ) -> PipelineRunReadiness:
        """Describe whether a queued run has an active compatible Worker."""

        workspace = await self._tenant_service.resolve(
            user_id=user_id, requested_project_id=requested_project_id,
        )
        document = await self._repository.get(
            project_id=workspace.project_id,
            pipeline_id=pipeline_id,
            run_id=run_id,
        )
        if document is None:
            raise PipelineRunNotFoundError(pipeline_id=pipeline_id, run_id=run_id)
        now = self._clock()
        if document.status != 'queued':
            return PipelineRunReadiness(
                status='not_applicable', project_id=document.project_id,
                required_harness=None, registered_worker_count=0,
                active_worker_count=0, compatible_worker_count=0,
                latest_heartbeat_at=None, observed_at=now,
            )
        harness = required_harness(document)
        if self._worker_service is None:
            raise RuntimeError('Worker readiness is not configured.')
        workers = await self._worker_service.readiness(
            project_id=document.project_id,
            harness=harness,
        )
        status: PipelineRunReadinessStatus = 'ready'
        if workers.registered_worker_count == 0:
            status = 'no_registered_workers'
        elif workers.active_worker_count == 0:
            status = 'no_active_workers'
        elif workers.compatible_worker_count == 0:
            status = 'no_compatible_workers'
        return PipelineRunReadiness(
            status=status, project_id=document.project_id,
            required_harness=harness,
            registered_worker_count=workers.registered_worker_count,
            active_worker_count=workers.active_worker_count,
            compatible_worker_count=workers.compatible_worker_count,
            latest_heartbeat_at=workers.latest_heartbeat_at,
            observed_at=now,
        )


def required_harness(document: PipelineRunDocument) -> dict[str, object]:
    """Return the frozen Harness for the step a Worker must claim."""

    if document.current_activity_run_id is not None:
        step = next(
            (
                candidate for candidate in document.steps
                if candidate.activity_run_id == document.current_activity_run_id
            ),
            None,
        )
    else:
        by_activity_id = {step.activity_id: step for step in document.steps}
        dependencies = snapshot_dependencies(document.pipeline_snapshot)
        step = next(
            (
                candidate for candidate in document.steps
                if candidate.status == 'pending'
                and all(
                    by_activity_id[item['activity_id']].status == item['condition']
                    for item in dependencies[candidate.activity_id]
                )
            ),
            None,
        )
    if step is None:
        raise RuntimeError('Pipeline run has no claimable step.')
    return harness_snapshot(step.activity_snapshot)
