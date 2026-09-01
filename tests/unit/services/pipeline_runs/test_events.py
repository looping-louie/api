"""Behavior tests for the PipelineRun execution event ledger."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from itertools import count

import pytest

from src.app.models.pipeline import (
    PipelineActivityStep,
    PipelineDetails,
    PipelineDocument,
    PipelineHarness,
)
from src.app.services.pipeline_runs.etag import pipeline_run_etag
from src.app.services.pipeline_runs.service import PipelineRunService
from src.app.services.shared.tenant import TenantService
from tests.contract_fixtures import load_harness_observation
from tests.conftest import IncrementingClock
from tests.unit.services.pipeline_runs.test_service import (
    InMemoryActivityRunRepository,
    InMemoryPipelineRunRepository,
    PipelineDetailsService,
    activity,
)
from tests.unit.services.pipeline_runs.test_snapshots import (
    StaticInstructionLibraryService,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('turn_completed', 'child_status', 'turn_event', 'step_event'),
    [
        (True, 'completed', 'harness_turn_completed', 'pipeline_step_completed'),
        (False, 'failed', 'harness_turn_failed', 'pipeline_step_failed'),
    ],
)
async def test_harness_pipeline_emits_claim_step_and_turn_events(
    tenant_service: TenantService,
    turn_completed: bool,
    child_status: str,
    turn_event: str,
    step_event: str,
) -> None:
    """The ledger captures scheduler state and normalized Harness outcomes."""

    now = datetime(2026, 8, 31, tzinfo=UTC)
    configured_activity = replace(
        activity('activity-1'),
        model_id='gpt-5-codex',
        harness=PipelineHarness(kind='codex_cli'),
        config={
            **activity('activity-1').config,
            'agents': [{'persona_id': 'persona-1', 'role': 'generator'}],
        },
    )
    details = PipelineDetails(
        document=PipelineDocument(
            id='pipeline-1', name='Pipeline', description='Run Codex.',
            status='active',
            steps=(PipelineActivityStep(activity_id=configured_activity.id),),
            created_at=now, created_by='user-1', updated_at=now,
            updated_by='user-1',
        ),
        activities=(configured_activity,),
    )
    runs = InMemoryPipelineRunRepository()
    identifiers = count(1)
    service = PipelineRunService(
        repository=runs,
        activity_run_repository=InMemoryActivityRunRepository(runs),
        pipeline_service=PipelineDetailsService(details),
        tenant_service=tenant_service,
        instruction_library_service=StaticInstructionLibraryService(),  # type: ignore[arg-type]
        id_factory=lambda: f'id-{next(identifiers)}',
        clock=IncrementingClock(),
        token_factory=lambda: 'lease-token',
    )
    created, _ = await service.create(
        user_id='user-1', pipeline_id='pipeline-1', input_text='Implement.',
        commit_mode='forbid',
    )
    queued, _ = await service.start(
        user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
    )
    claimed, child, _ = await service.claim(
        user_id='user-1', pipeline_id='pipeline-1', run_id=created.id,
        worker_id='worker-1', if_match=pipeline_run_etag(queued),
        lease_duration=timedelta(minutes=1),
    )
    artifacts = load_harness_observation(
        'codex_cli_v1_completed.json'
        if turn_completed else 'codex_cli_v1_failed.json'
    )
    runs.children[child.id] = replace(
        child,
        status=child_status,
        state=child_status,
        next_action='none',
        continuation_token=None,
        execution_context={'runtime_artifacts': artifacts},
    )

    completed, _ = await service.continue_run(
        user_id='user-1', pipeline_id='pipeline-1', run_id=claimed.id,
        lease_token='lease-token',
    )
    with_events, _ = await service.get(
        user_id='user-1', pipeline_id='pipeline-1', run_id=completed.id,
    )

    assert [event.event_type for event in with_events.events] == [
        'pipeline_run_created',
        'pipeline_run_claimed',
        'pipeline_step_started',
        turn_event,
        step_event,
    ]
    harness_event = with_events.events[3]
    assert harness_event.actor_id == 'worker-1'
    assert harness_event.payload == {'activity_run_id': child.id, **artifacts}
