"""Behavior tests for dependency-aware pipeline scheduling."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from itertools import count
from types import SimpleNamespace

import pytest

from src.app.models.activity import ActivityDocument
from src.app.models.activity_run import ActivityRunDocument
from src.app.models.pipeline import (
    PipelineActivityStep,
    PipelineDetails,
    PipelineDocument,
    PipelineHarness,
    PipelineStepDependency,
)
from src.app.models.pipeline_run import PipelineRunDocument
from src.app.models.user import UserDocument, UserSettings
from src.app.services.pipeline_runs.etag import pipeline_run_etag
from src.app.services.pipeline_runs.service import PipelineRunService
from src.app.services.pipeline_runs.types import (
    PipelineRunPreconditionFailedError,
    PipelineRunUnavailableError,
)
from src.app.services.shared.tenant import TenantService
from src.app.services.workers import (
    WorkerHarnessUnavailableError,
    WorkerUnavailableError,
)
from tests.conftest import IncrementingClock


class InMemoryPipelineRunRepository:
    """Store pipeline runs and children while exercising scheduler contracts."""

    def __init__(self) -> None:
        """Initialize empty persisted run and child collections."""

        self.document: PipelineRunDocument | None = None
        self.children: dict[str, ActivityRunDocument] = {}
        self.events = []

    async def create(
        self, *, document: PipelineRunDocument, activity_run: ActivityRunDocument | None,
    ) -> PipelineRunDocument:
        """Persist the initial scheduler state and optional child."""

        self.document = document
        self.events.extend(document.events)
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
        return replace(self.document, events=())

    async def start(
        self,
        *,
        document: PipelineRunDocument,
        expected_updated_at: datetime,
        activity_run: ActivityRunDocument | None,
    ) -> bool:
        """Persist a prepared run's first scheduler decision."""

        if (
            self.document is None
            or self.document.status != 'prepared'
            or self.document.updated_at != expected_updated_at
        ):
            return False
        self.document = document
        self.events.extend(document.events)
        if activity_run is not None:
            self.children[activity_run.id] = activity_run
        return True

    async def list_events(
        self, *, workspace_id: str, pipeline_id: str, run_id: str,
    ) -> list[object]:
        """Return immutable events under the run's verified ownership."""

        if self.document is None or (workspace_id, pipeline_id, run_id) != (
            self.document.workspace_id,
            self.document.pipeline_id,
            self.document.id,
        ):
            return []
        return list(self.events)

    async def list_claimable(
        self, *, workspace_id: str, pipeline_id: str, claimed_before: datetime,
    ) -> list[PipelineRunDocument]:
        """Return the stored queued or expired run beneath one Pipeline."""

        if self.document is None or (self.document.workspace_id, self.document.pipeline_id) != (
            workspace_id,
            pipeline_id,
        ):
            return []
        if self.document.status == 'queued':
            return [self.document]
        if (
            self.document.status != 'claimed'
            or self.document.lease_expires_at is None
            or self.document.lease_expires_at > claimed_before
        ):
            return []
        return [self.document]

    async def claim(
        self, *, document: PipelineRunDocument, expected_updated_at: datetime,
        expected_current_activity_run_id: str | None,
        activity_run: ActivityRunDocument | None,
    ) -> bool:
        """Replace the observed run and persist an initial child when supplied."""

        if (
            self.document is None
            or self.document.updated_at != expected_updated_at
            or self.document.current_activity_run_id != expected_current_activity_run_id
        ):
            return False
        self.document = document
        self.events.extend(document.events)
        if activity_run is not None:
            self.children[activity_run.id] = activity_run
        return True

    async def renew_lease(
        self,
        *,
        document: PipelineRunDocument,
        expected_lease_token: str | None,
        now: datetime,
    ) -> bool:
        """Extend the active lease only when the existing token still matches."""

        if (
            self.document is None
            or self.document.lease_token != expected_lease_token
            or self.document.lease_expires_at is None
            or self.document.lease_expires_at <= now
        ):
            return False
        self.document = replace(
            self.document,
            lease_expires_at=document.lease_expires_at,
            updated_at=document.updated_at,
        )
        return True

    async def transition(
        self, *, document: PipelineRunDocument,
        expected_current_activity_run_id: str | None,
        expected_lease_token: str,
        now: datetime,
        activity_run: ActivityRunDocument | None,
    ) -> bool:
        """Persist a transition only for the currently scheduled child."""

        active_worker = (
            self.document is not None
            and self.document.lease_token == expected_lease_token
            and self.document.lease_expires_at is not None
            and self.document.lease_expires_at > now
        )
        waiting_human = (
            self.document is not None
            and self.document.status == 'waiting'
            and self.document.lease_token is None
            and expected_lease_token is None
        )
        if (
            self.document is None
            or self.document.current_activity_run_id != expected_current_activity_run_id
            or not (active_worker or waiting_human)
        ):
            return False
        self.document = document
        self.events.extend(document.events)
        if activity_run is not None:
            self.children[activity_run.id] = activity_run
        return True


class InMemoryWorkerService:
    """Control worker claim admission for PipelineRun scheduler tests."""

    def __init__(self, *, active: bool, supports_harness: bool = True) -> None:
        """Store whether registration liveness should admit claims."""

        self.active = active
        self.supports_harness = supports_harness
        self.calls: list[tuple[str, str]] = []
        self.harness_calls: list[tuple[str, str, dict[str, object]]] = []

    async def require_active(self, *, workspace_id: str, worker_id: str) -> None:
        """Record one admission check and reject inactive worker identities."""

        self.calls.append((workspace_id, worker_id))
        if not self.active:
            raise WorkerUnavailableError(worker_id)

    async def require_harness(
        self,
        *,
        workspace_id: str,
        worker_id: str,
        harness: dict[str, object],
    ) -> None:
        """Record one capability admission check and reject mismatches."""

        self.harness_calls.append((workspace_id, worker_id, harness))
        if not self.supports_harness:
            raise WorkerHarnessUnavailableError(worker_id)


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


class StaticUserService:
    """Return one user with a fixed execution default for scheduler tests."""

    def __init__(self, document: UserDocument) -> None:
        """Store the user returned by every lookup."""

        self._document = document

    async def get(self, **_: object) -> UserDocument:
        """Return the configured current user."""

        return self._document


class StaticModelExecutionService:
    """Select one deterministic linked service for frozen Louie snapshots."""

    async def select_linked_service(
        self,
        *,
        user_id: str,
        **_: object,
    ) -> SimpleNamespace:
        """Return the service selected by this focused scheduler fixture."""

        return SimpleNamespace(
            id='linked-service-selected',
            user_id=user_id,
        )


def activity(
    activity_id: str,
    activity_type: str = 'direct_loop',
) -> ActivityDocument:
    """Build one active Activity for a Pipeline scheduler test."""

    now = datetime(2026, 8, 14, tzinfo=UTC)
    return ActivityDocument(
        id=activity_id, workspace_id='workspace-1', name=activity_id,
        description='Complete one pipeline step.', status='active', type=activity_type,
        config={'stop_conditions': {'max_iterations': 1}, 'agents': [], 'output_contract': {'type': 'text', 'description': 'Result.'}},
        created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
    )


@pytest.mark.asyncio
async def test_create_freezes_agent_activity_and_pipeline_execution_defaults(
    tenant_service: TenantService,
) -> None:
    """Narrower agent and Activity values override Pipeline candidates."""

    now = datetime(2026, 8, 25, tzinfo=UTC)
    first = replace(
        activity('activity-1'),
        model_id='model-activity',
        harness=PipelineHarness(kind='codex_cli'),
        config={
            **activity('activity-1').config,
            'agents': [
                {
                    'model_id': 'model-agent',
                    'persona_id': 'persona-1',
                    'role': 'generator',
                },
            ],
        },
    )
    second = replace(
        activity('activity-2'),
        config={
            **activity('activity-2').config,
            'agents': [
                {
                    'persona_id': 'persona-2',
                    'role': 'generator',
                },
            ],
        },
    )
    details = PipelineDetails(
        document=PipelineDocument(
            id='pipeline-1', workspace_id='workspace-1', name='Pipeline',
            description='Run configured steps.', status='active',
            steps=(
                PipelineActivityStep(activity_id=first.id),
                PipelineActivityStep(activity_id=second.id),
            ),
            model_id='model-pipeline',
            harness=PipelineHarness(kind='louie'),
            created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
        ),
        activities=(first, second),
    )
    runs = InMemoryPipelineRunRepository()
    service = PipelineRunService(
        repository=runs,
        activity_run_repository=InMemoryActivityRunRepository(runs),
        pipeline_service=PipelineDetailsService(details),
        tenant_service=tenant_service,
        model_execution_service=StaticModelExecutionService(),  # type: ignore[arg-type]
        id_factory=lambda: 'run-1',
        clock=IncrementingClock(),
    )

    created, _ = await service.create(
        user_id='user-1', pipeline_id='pipeline-1', input_text='Implement.',
    )

    first_agent = created.steps[0].activity_snapshot['agents'][0]
    second_agent = created.steps[1].activity_snapshot['agents'][0]
    assert created.pipeline_snapshot['harness']['kind'] == 'louie'
    assert created.steps[0].activity_snapshot['harness']['kind'] == 'codex_cli'
    assert first_agent['model_id'] == 'model-agent'
    assert 'model_id' not in second_agent
    assert second_agent['model_target'] == {
        'linked_service_id': 'linked-service-selected',
        'linked_service_user_id': 'user-1',
        'model_id': 'model-pipeline',
    }


@pytest.mark.asyncio
async def test_create_freezes_user_execution_defaults_when_unset(
    tenant_service: TenantService,
) -> None:
    """User candidates supply otherwise unset Pipeline and Activity values."""

    now = datetime(2026, 8, 25, tzinfo=UTC)
    configured_activity = replace(
        activity('activity-1'),
        config={
            **activity('activity-1').config,
            'agents': [
                {
                    'persona_id': 'persona-1',
                    'role': 'generator',
                },
            ],
        },
    )
    details = PipelineDetails(
        document=PipelineDocument(
            id='pipeline-1', workspace_id='workspace-1', name='Pipeline',
            description='Run configured steps.', status='active',
            steps=(PipelineActivityStep(activity_id=configured_activity.id),),
            created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
        ),
        activities=(configured_activity,),
    )
    runs = InMemoryPipelineRunRepository()
    service = PipelineRunService(
        repository=runs,
        activity_run_repository=InMemoryActivityRunRepository(runs),
        pipeline_service=PipelineDetailsService(details),
        tenant_service=tenant_service,
        user_service=StaticUserService(UserDocument(  # type: ignore[arg-type]
            id='user-1', created_at=now, updated_at=now,
            settings=UserSettings(
                default_model_id='model-user',
                default_harness=PipelineHarness(kind='codex_cli'),
            ),
        )),
        id_factory=lambda: 'run-1',
        clock=IncrementingClock(),
    )

    created, _ = await service.create(
        user_id='user-1', pipeline_id='pipeline-1', input_text='Implement.',
    )

    assert created.pipeline_snapshot['harness']['kind'] == 'codex_cli'
    assert created.steps[0].activity_snapshot['harness']['kind'] == 'codex_cli'
    assert 'model_id' not in created.steps[0].activity_snapshot['agents'][0]


@pytest.mark.asyncio
async def test_create_freezes_user_default_harness_when_higher_scopes_are_unset(
    tenant_service: TenantService,
) -> None:
    """User settings provide the final Harness candidate for every step."""

    now = datetime(2026, 8, 25, tzinfo=UTC)
    configured_activity = activity('activity-1')
    details = PipelineDetails(
        document=PipelineDocument(
            id='pipeline-1', workspace_id='workspace-1', name='Pipeline',
            description='Run configured steps.', status='active',
            steps=(PipelineActivityStep(activity_id=configured_activity.id),),
            created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
        ),
        activities=(configured_activity,),
    )
    runs = InMemoryPipelineRunRepository()
    service = PipelineRunService(
        repository=runs,
        activity_run_repository=InMemoryActivityRunRepository(runs),
        pipeline_service=PipelineDetailsService(details),
        tenant_service=tenant_service,
        user_service=StaticUserService(UserDocument(  # type: ignore[arg-type]
            id='user-1', created_at=now, updated_at=now,
            settings=UserSettings(default_harness=PipelineHarness(kind='codex_cli')),
        )),
        id_factory=lambda: 'run-1',
        clock=IncrementingClock(),
    )

    created, _ = await service.create(
        user_id='user-1', pipeline_id='pipeline-1', input_text='Implement.',
    )

    assert created.pipeline_snapshot['harness']['kind'] == 'codex_cli'
    assert created.steps[0].activity_snapshot['harness']['kind'] == 'codex_cli'


@pytest.mark.asyncio
async def test_prepared_run_starts_before_runtime_claim(
    tenant_service: TenantService,
) -> None:
    """An operator start makes a prepared runtime run available for claims."""

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
    workers = InMemoryWorkerService(active=True)
    service = PipelineRunService(
        repository=runs, activity_run_repository=InMemoryActivityRunRepository(runs),
        pipeline_service=PipelineDetailsService(details), tenant_service=tenant_service,
        worker_service=workers,
        id_factory=lambda: 'run-1', clock=IncrementingClock(),
        token_factory=lambda: 'token',
    )

    created, child = await service.create(
        user_id='user-1', pipeline_id='pipeline-1', input_text='Implement.',
        commit_mode='forbid',
    )

    assert created.status == 'prepared'
    assert created.commit_mode == 'forbid'
    assert created.current_activity_run_id is None
    assert created.pipeline_snapshot['harness'] == {
        'kind': 'louie',
        'version': 'v1',
        'config': {},
    }
    assert [step.status for step in created.steps] == ['pending']
    assert child is None
    assert runs.children == {}

    candidates = await service.list_claimable(
        user_id='user-1', pipeline_id='pipeline-1',
    )

    assert candidates == []

    started, started_child = await service.start(
        user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
    )

    assert started.status == 'queued'
    assert started_child is None
    candidates = await service.list_claimable(
        user_id='user-1', pipeline_id='pipeline-1',
    )
    assert candidates == [started]

    claim = await service.claim(
        user_id='user-1', pipeline_id='pipeline-1', run_id=started.id,
        worker_id='worker-1', if_match=pipeline_run_etag(started),
        lease_duration=timedelta(minutes=1),
    )

    assert claim is not None
    claimed, claimed_child, lease_token = claim
    assert claimed.status == 'claimed'
    assert claimed.worker_id == 'worker-1'
    assert claimed.attempt == 1
    assert claimed_child.activity_id == first.id
    assert claimed_child.activity_snapshot['commit_mode'] == 'forbid'
    assert claimed_child.activity_snapshot['harness'] == {
        'kind': 'louie',
        'version': 'v1',
        'config': {},
    }
    assert lease_token == 'token'
    assert workers.calls == [('workspace-1', 'worker-1')]
    assert workers.harness_calls == [(
        'workspace-1',
        'worker-1',
        {'kind': 'louie', 'version': 'v1', 'config': {}},
    )]

    runs.document = replace(
        claimed,
        lease_expires_at=datetime(1970, 1, 1, tzinfo=UTC),
    )
    reclaimed = await service.claim(
        user_id='user-1', pipeline_id='pipeline-1', run_id=claimed.id,
        worker_id='worker-2', if_match=pipeline_run_etag(runs.document),
        lease_duration=timedelta(minutes=1),
    )

    assert reclaimed is not None
    reclaimed_run, reclaimed_child, _ = reclaimed
    assert reclaimed_run.worker_id == 'worker-2'
    assert reclaimed_run.attempt == 2
    assert reclaimed_child.id == claimed_child.id
    assert len(runs.children) == 1

    workers.active = False
    with pytest.raises(WorkerUnavailableError):
        await service.claim(
            user_id='user-1', pipeline_id='pipeline-1', run_id=claimed.id,
            worker_id='worker-3', if_match=pipeline_run_etag(runs.document),
            lease_duration=timedelta(minutes=1),
        )

    workers.active = True
    with pytest.raises(PipelineRunPreconditionFailedError):
        await service.claim(
            user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
            worker_id='worker-3', if_match=pipeline_run_etag(created),
            lease_duration=timedelta(minutes=1),
        )


@pytest.mark.asyncio
async def test_claim_rejects_an_active_worker_without_the_pipeline_harness(
    tenant_service: TenantService,
) -> None:
    """Worker liveness does not authorize an incompatible Harness claim."""

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
    workers = InMemoryWorkerService(active=True, supports_harness=False)
    service = PipelineRunService(
        repository=runs, activity_run_repository=InMemoryActivityRunRepository(runs),
        pipeline_service=PipelineDetailsService(details), tenant_service=tenant_service,
        worker_service=workers, id_factory=lambda: 'run-1',
        clock=IncrementingClock(), token_factory=lambda: 'token',
    )
    created, _ = await service.create(
        user_id='user-1', pipeline_id='pipeline-1', input_text='Implement.',
    )
    started, _ = await service.start(
        user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
    )

    with pytest.raises(WorkerHarnessUnavailableError):
        await service.claim(
            user_id='user-1', pipeline_id='pipeline-1', run_id=started.id,
            worker_id='worker-1', if_match=pipeline_run_etag(started),
            lease_duration=timedelta(minutes=1),
        )


@pytest.mark.asyncio
async def test_active_claim_can_renew_its_lease_but_stale_claim_cannot(
    tenant_service: TenantService,
) -> None:
    """Only the active, unexpired worker token can extend a Pipeline lease."""

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
    clock = IncrementingClock()
    service = PipelineRunService(
        repository=runs, activity_run_repository=InMemoryActivityRunRepository(runs),
        pipeline_service=PipelineDetailsService(details), tenant_service=tenant_service,
        id_factory=lambda: 'run-1', clock=clock, token_factory=lambda: 'token',
    )
    created, _ = await service.create(
        user_id='user-1', pipeline_id='pipeline-1', input_text='Implement.',
    )
    started, _ = await service.start(
        user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
    )
    claim = await service.claim(
        user_id='user-1', pipeline_id='pipeline-1', run_id=started.id,
        worker_id='worker-1', if_match=pipeline_run_etag(started),
        lease_duration=timedelta(minutes=1),
    )

    assert claim is not None
    renewed = await service.renew_lease(
        user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
        lease_token='token', lease_duration=timedelta(minutes=1),
    )

    assert renewed.lease_expires_at is not None
    assert renewed.lease_expires_at > claim[0].lease_expires_at
    with pytest.raises(PipelineRunUnavailableError, match='lease is no longer active'):
        await service.renew_lease(
            user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
            lease_token='stale-token', lease_duration=timedelta(minutes=1),
        )


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
    started, _ = await service.start(
        user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
    )
    claim = await service.claim(
        user_id='user-1', pipeline_id='pipeline-1', run_id=started.id,
        worker_id='worker-1', if_match=pipeline_run_etag(started),
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
        lease_token='token',
    )

    assert second_child is not None and second_child.activity_id == second.id
    assert [step.status for step in advanced.steps] == ['completed', 'in_progress']
    with pytest.raises(PipelineRunUnavailableError, match='lease is no longer active'):
        await service.continue_run(
            user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
            lease_token='stale-token',
        )


@pytest.mark.asyncio
async def test_started_human_activity_creates_a_waiting_child_run(
    tenant_service: TenantService,
) -> None:
    """Starting schedules an approval child run without a runtime claim."""

    gate = activity('approval-1', 'approval')
    now = datetime(2026, 8, 14, tzinfo=UTC)
    details = PipelineDetails(
        document=PipelineDocument(
            id='pipeline-1', workspace_id='workspace-1', name='Pipeline',
            description='Wait for approval.', status='active',
            steps=(PipelineActivityStep(activity_id=gate.id),),
            created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
        ),
        activities=(gate,),
    )
    runs = InMemoryPipelineRunRepository()
    identifiers = count(1)
    service = PipelineRunService(
        repository=runs, activity_run_repository=InMemoryActivityRunRepository(runs),
        pipeline_service=PipelineDetailsService(details), tenant_service=tenant_service,
        id_factory=lambda: f'id-{next(identifiers)}', clock=IncrementingClock(),
        token_factory=lambda: 'token',
    )
    created, child = await service.create(
        user_id='user-1', pipeline_id='pipeline-1', input_text='Implement.',
    )

    candidates = await service.list_claimable(
        user_id='user-1', pipeline_id='pipeline-1',
    )

    assert created.status == 'prepared'
    assert child is None
    assert candidates == []

    waiting, child = await service.start(
        user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
    )

    assert waiting.status == 'waiting'
    assert child is not None
    assert child.activity_id == gate.id
    assert child.state == 'awaiting_human_decision'
    assert child.next_action == 'submit_human_decision'
    assert waiting.worker_id is None
    runs.children[child.id] = replace(
        child,
        status='completed',
        state='completed',
        next_action='none',
        continuation_token=None,
        execution_context={'human_decision': {'decision': 'approved'}},
    )
    completed, next_child = await service.continue_run(
        user_id='user-1', pipeline_id='pipeline-1', run_id=waiting.id,
        lease_token=None,
    )

    assert completed.status == 'completed'
    assert completed.steps[0].status == 'completed'
    assert next_child is None


@pytest.mark.asyncio
async def test_rejected_human_activity_reruns_ancestors_before_retry(
    tenant_service: TenantService,
) -> None:
    """A rejected human run clears predecessor output before its retry."""

    first, gate = activity('activity-1'), activity('approval-1', 'approval')
    now = datetime(2026, 8, 14, tzinfo=UTC)
    details = PipelineDetails(
        document=PipelineDocument(
            id='pipeline-1', workspace_id='workspace-1', name='Pipeline',
            description='Correct then approve.', status='active',
            steps=(
                PipelineActivityStep(activity_id=first.id),
                PipelineActivityStep(
                    activity_id=gate.id,
                    depends_on=(
                        PipelineStepDependency(activity_id=first.id, condition='success'),
                    ),
                ),
            ),
            created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
        ),
        activities=(first, gate),
    )
    runs = InMemoryPipelineRunRepository()
    identifiers = count(1)
    service = PipelineRunService(
        repository=runs, activity_run_repository=InMemoryActivityRunRepository(runs),
        pipeline_service=PipelineDetailsService(details), tenant_service=tenant_service,
        id_factory=lambda: f'id-{next(identifiers)}', clock=IncrementingClock(),
        token_factory=lambda: 'token',
    )
    created, _ = await service.create(
        user_id='user-1', pipeline_id='pipeline-1', input_text='Implement.',
    )
    started, _ = await service.start(
        user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
    )
    _, first_child, _ = await service.claim(
        user_id='user-1', pipeline_id='pipeline-1', run_id=started.id,
        worker_id='worker-1', if_match=pipeline_run_etag(started),
        lease_duration=timedelta(minutes=1),
    )
    assert first_child is not None
    runs.children[first_child.id] = replace(
        first_child, status='completed', state='completed', next_action='none',
        continuation_token=None,
    )
    waiting, child = await service.continue_run(
        user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
        lease_token='token',
    )
    assert waiting.status == 'waiting'
    assert child is not None
    runs.children[child.id] = replace(
        child,
        status='failed',
        state='failed',
        next_action='none',
        continuation_token=None,
        execution_context={'human_decision': {'decision': 'rejected'}},
    )
    rejected, next_child = await service.continue_run(
        user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
        lease_token=None,
    )

    assert rejected.status == 'queued'
    assert [step.status for step in rejected.steps] == ['pending', 'pending']
    assert rejected.steps[0].activity_run_id is None
    assert next_child is None

    _, corrected_child, token = await service.claim(
        user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
        worker_id='worker-2', if_match=pipeline_run_etag(rejected),
        lease_duration=timedelta(minutes=1),
    )
    assert corrected_child is not None
    runs.children[corrected_child.id] = replace(
        corrected_child, status='completed', state='completed', next_action='none',
        continuation_token=None,
    )
    reopened, child = await service.continue_run(
        user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
        lease_token=token or '',
    )

    assert reopened.status == 'waiting'
    assert child is not None
    assert child.state == 'awaiting_human_decision'
