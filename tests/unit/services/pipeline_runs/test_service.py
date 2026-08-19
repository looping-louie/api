"""Behavior tests for dependency-aware pipeline scheduling."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from itertools import count

import pytest

from src.app.models.activity import ActivityDocument
from src.app.models.activity_run import ActivityRunDocument
from src.app.models.pipeline import (
    PipelineActivityStep,
    PipelineDetails,
    PipelineDocument,
    PipelineStepDependency,
)
from src.app.models.pipeline_run import PipelineRunDocument
from src.app.services.pipeline_runs.service import PipelineRunService
from src.app.services.shared.tenant import TenantService
from tests.conftest import IncrementingClock


class InMemoryPipelineRunRepository:
    """Store pipeline runs and children while exercising scheduler contracts."""

    def __init__(self) -> None:
        """Initialize empty persisted run and child collections."""

        self.document: PipelineRunDocument | None = None
        self.children: dict[str, ActivityRunDocument] = {}

    async def create(
        self, *, document: PipelineRunDocument, activity_run: ActivityRunDocument | None,
    ) -> PipelineRunDocument:
        """Persist the initial scheduler state and optional child."""

        self.document = document
        if activity_run is not None:
            self.children[activity_run.id] = activity_run
        return document

    async def get(
        self, *, workspace_id: str, pipeline_id: str, run_id: str,
    ) -> PipelineRunDocument | None:
        """Return the stored run only when its ownership matches."""

        if self.document is None:
            return None
        if (workspace_id, pipeline_id, run_id) != (
            self.document.workspace_id, self.document.pipeline_id, self.document.id,
        ):
            return None
        return self.document

    async def find_claimable(
        self, *, workspace_id: str, claimed_before: datetime,
    ) -> PipelineRunDocument | None:
        """Return the stored queued or expired run in the workspace."""

        if self.document is None or self.document.workspace_id != workspace_id:
            return None
        if self.document.status == 'queued':
            return self.document
        if (
            self.document.status != 'claimed'
            or self.document.lease_expires_at is None
            or self.document.lease_expires_at > claimed_before
        ):
            return None
        return self.document

    async def claim(
        self, *, document: PipelineRunDocument, expected_updated_at: datetime,
        activity_run: ActivityRunDocument | None,
    ) -> bool:
        """Replace the observed run and persist an initial child when supplied."""

        if self.document is None or self.document.updated_at != expected_updated_at:
            return False
        self.document = document
        if activity_run is not None:
            self.children[activity_run.id] = activity_run
        return True

    async def transition(
        self, *, document: PipelineRunDocument,
        expected_current_activity_run_id: str | None,
        activity_run: ActivityRunDocument | None,
    ) -> bool:
        """Persist a transition only for the currently scheduled child."""

        if self.document is None or self.document.current_activity_run_id != expected_current_activity_run_id:
            return False
        self.document = document
        if activity_run is not None:
            self.children[activity_run.id] = activity_run
        return True


class InMemoryActivityRunRepository:
    """Expose child activity runs created by the pipeline scheduler."""

    def __init__(self, run_repository: InMemoryPipelineRunRepository) -> None:
        """Store the shared child run collection."""

        self._run_repository = run_repository

    async def get(
        self, *, workspace_id: str, activity_id: str, run_id: str,
    ) -> ActivityRunDocument | None:
        """Return the requested child when its activity ownership matches."""

        child = self._run_repository.children.get(run_id)
        if child is None or (child.workspace_id, child.activity_id) != (workspace_id, activity_id):
            return None
        return child


class PipelineDetailsService:
    """Return the immutable pipeline details supplied to the scheduler."""

    def __init__(self, details: PipelineDetails) -> None:
        """Store the details returned by every describe call."""

        self._details = details

    async def describe(self, **_: object) -> PipelineDetails:
        """Return the configured pipeline definition and activities."""

        return self._details


def activity(activity_id: str) -> ActivityDocument:
    """Build one executable direct-loop activity."""

    now = datetime(2026, 8, 14, tzinfo=UTC)
    return ActivityDocument(
        id=activity_id, workspace_id='workspace-1', name=activity_id,
        description='Complete one pipeline step.', status='active', type='direct_loop',
        config={'stop_conditions': {'max_iterations': 1}, 'agents': [], 'output_contract': {'type': 'text', 'description': 'Result.'}},
        created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
    )


@pytest.mark.asyncio
async def test_created_run_waits_for_runtime_claim(
    tenant_service: TenantService,
) -> None:
    """Creation leaves the first Activity unallocated until a worker claims it."""

    first = activity('activity-1')
    now = datetime(2026, 8, 14, tzinfo=UTC)
    details = PipelineDetails(
        document=PipelineDocument(
            id='pipeline-1', workspace_id='workspace-1', name='Pipeline',
            description='Run one step.', status='active',
            steps=(PipelineActivityStep(activity_id=first.id),),
            created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
        ),
        activities=(first,),
    )
    runs = InMemoryPipelineRunRepository()
    service = PipelineRunService(
        repository=runs, activity_run_repository=InMemoryActivityRunRepository(runs),
        pipeline_service=PipelineDetailsService(details), tenant_service=tenant_service,
        id_factory=lambda: 'run-1', clock=IncrementingClock(),
        token_factory=lambda: 'token',
    )

    created, child = await service.create(
        user_id='user-1', pipeline_id='pipeline-1', input_text='Implement.',
    )

    assert created.status == 'queued'
    assert created.current_activity_run_id is None
    assert [step.status for step in created.steps] == ['pending']
    assert child is None
    assert runs.children == {}

    claim = await service.claim_next(
        user_id='user-1', worker_id='worker-1',
        lease_duration=timedelta(minutes=1),
    )

    assert claim is not None
    claimed, claimed_child, lease_token = claim
    assert claimed.status == 'claimed'
    assert claimed.worker_id == 'worker-1'
    assert claimed.attempt == 1
    assert claimed_child.activity_id == first.id
    assert lease_token == 'token'

    runs.document = replace(
        claimed,
        lease_expires_at=datetime(1970, 1, 1, tzinfo=UTC),
    )
    reclaimed = await service.claim_next(
        user_id='user-1', worker_id='worker-2',
        lease_duration=timedelta(minutes=1),
    )

    assert reclaimed is not None
    reclaimed_run, reclaimed_child, _ = reclaimed
    assert reclaimed_run.worker_id == 'worker-2'
    assert reclaimed_run.attempt == 2
    assert reclaimed_child.id == claimed_child.id
    assert len(runs.children) == 1


@pytest.mark.asyncio
async def test_completed_step_schedules_success_dependent_child(
    tenant_service: TenantService,
) -> None:
    """A completed child unlocks and persists its success-dependent step."""

    first, second = activity('activity-1'), activity('activity-2')
    now = datetime(2026, 8, 14, tzinfo=UTC)
    details = PipelineDetails(
        document=PipelineDocument(
            id='pipeline-1', workspace_id='workspace-1', name='Pipeline',
            description='Run two steps.', status='active',
            steps=(
                PipelineActivityStep(activity_id=first.id),
                PipelineActivityStep(
                    activity_id=second.id,
                    depends_on=(PipelineStepDependency(activity_id=first.id, condition='success'),),
                ),
            ),
            created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
        ),
        activities=(first, second),
    )
    runs = InMemoryPipelineRunRepository()
    identifiers = count(1)
    service = PipelineRunService(
        repository=runs, activity_run_repository=InMemoryActivityRunRepository(runs),
        pipeline_service=PipelineDetailsService(details), tenant_service=tenant_service,
        id_factory=lambda: f'run-{next(identifiers)}', clock=IncrementingClock(),
        token_factory=lambda: 'token',
    )

    created, child = await service.create(
        user_id='user-1', pipeline_id='pipeline-1', input_text='Implement.',
    )
    assert child is None
    claim = await service.claim_next(
        user_id='user-1', worker_id='worker-1',
        lease_duration=timedelta(minutes=1),
    )
    assert claim is not None
    _, first_child, _ = claim
    assert first_child is not None and first_child.activity_id == first.id

    runs.children[first_child.id] = replace(
        first_child, status='completed', state='completed', next_action='none',
        continuation_token=None,
    )
    advanced, second_child = await service.continue_run(
        user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
    )

    assert second_child is not None and second_child.activity_id == second.id
    assert [step.status for step in advanced.steps] == ['completed', 'in_progress']
