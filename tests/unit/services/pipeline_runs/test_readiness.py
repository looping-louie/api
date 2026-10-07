"""Tests for queued Pipeline worker-readiness diagnostics."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.app.models.pipeline_run import PipelineRunDocument, PipelineRunStepDocument
from src.app.models.worker import WorkerReadinessDocument
from src.app.services.pipeline_runs.readiness import PipelineRunReadinessService
from src.app.services.shared.tenant import TenantService


class ReadinessRunRepository:
    """Return one deterministic frozen queued run."""

    def __init__(self, document: PipelineRunDocument) -> None:
        """Store the run returned by ownership-scoped reads."""

        self.document = document

    async def get(self, **_: object) -> PipelineRunDocument:
        """Return the configured queued run."""

        return self.document


class ReadinessWorkerInstanceService:
    """Return deterministic global Worker aggregates."""

    def __init__(self, summary: WorkerReadinessDocument) -> None:
        """Store the Worker aggregate and observed Harness."""

        self.summary = summary
        self.harness: dict[str, object] | None = None

    async def readiness(
        self, *, project_id: str, harness: dict[str, object],
    ) -> WorkerReadinessDocument:
        """Record the frozen Harness and return the aggregate."""

        assert project_id == 'workspace-1'
        self.harness = harness
        return self.summary


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('counts', 'expected_status'),
    [
        ((0, 0, 0), 'no_registered_workers'),
        ((2, 0, 0), 'no_active_workers'),
        ((2, 1, 0), 'no_compatible_workers'),
        ((2, 1, 1), 'ready'),
    ],
)
async def test_queued_run_readiness_uses_the_next_step_harness(
    tenant_service: TenantService,
    counts: tuple[int, int, int],
    expected_status: str,
) -> None:
    """Diagnostics classify Workers against the next Activity's frozen Harness."""

    now = datetime(2026, 8, 26, tzinfo=UTC)
    document = PipelineRunDocument(
        id='run-1', project_id='workspace-1', pipeline_id='pipeline-1',
        input='Implement.', status='queued', worker_id=None, lease_token=None,
        lease_expires_at=None, attempt=0, current_activity_run_id=None,
        pipeline_snapshot={
            'harness': {'kind': 'louie', 'version': 'v1', 'config': {}},
            'steps': [{'activity_id': 'activity-1', 'depends_on': []}],
        },
        steps=(PipelineRunStepDocument(
            position=0, activity_id='activity-1', status='pending',
            activity_run_id=None,
            activity_snapshot={
                'harness': {'kind': 'codex_cli', 'version': 'v1', 'config': {}},
            },
            updated_at=now,
        ),),
        created_at=now, created_by='user-1', updated_at=now,
    )
    workers = ReadinessWorkerInstanceService(WorkerReadinessDocument(
        registered_worker_count=counts[0], active_worker_count=counts[1],
        compatible_worker_count=counts[2], latest_heartbeat_at=None,
    ))
    service = PipelineRunReadinessService(
        repository=ReadinessRunRepository(document),
        tenant_service=tenant_service,
            worker_instance_service=workers,
        clock=lambda: now,
    )

    readiness = await service.get(
        user_id='user-1', pipeline_id='pipeline-1', run_id='run-1',
    )

    assert readiness.status == expected_status
    assert readiness.project_id == 'workspace-1'
    assert readiness.required_harness == {
        'kind': 'codex_cli', 'version': 'v1', 'config': {},
    }
    assert workers.harness == readiness.required_harness
