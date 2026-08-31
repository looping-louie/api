"""Tests for Codex commit-message handoff through Activity checkpoints."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.app.controllers.activity_runs.utils import activity_run_response
from src.app.models.activity import ActivityDocument
from src.app.models.activity_run import ActivityRunDocument
from src.app.services.activity_runs.service import ActivityRunService
from src.app.services.activity_runs.types import ActivityRunValidationError
from src.app.services.shared.tenant import TenantService
from tests.unit.services.activity_runs.test_harness_routing import (
    _ActivityRunRepository,
    _ActivityService,
)


@pytest.mark.asyncio
async def test_completed_codex_turn_publishes_commit_message(
    tenant_service: TenantService,
) -> None:
    """A successful Codex result carries its message into commit authorization."""

    service, repository, activity = _service(
        tenant_service=tenant_service,
        commit_mode='allow',
    )

    result = await service.continue_run(
        user_id='user-1', activity_id=activity.id, run_id='run-1',
        pipeline_run_id='pipeline-run-1', lease_token='lease-1',
        continuation_token='token-1', idempotency_key='harness-1',
        action='run_harness',
        result={
            **_harness_result(),
            'commit_message': 'feat: implement requested change',
        },
    )

    assert result.next_action == 'commit_if_allowed'
    expected_artifacts = {
        'completed': True,
        'started_at': '2026-08-31T10:00:00+00:00',
        'completed_at': '2026-08-31T10:00:02+00:00',
        'duration_ms': 2000,
        'commit_message': 'feat: implement requested change',
        'requested_model': 'gpt-5-codex',
        'actual_model': 'gpt-5.1-codex',
        'reasoning_effort': 'high',
        'session_reference': 'thread-1',
        'usage': {'input_tokens': 10, 'reasoning_output_tokens': 3},
        'exit_code': 0,
        'diagnostics': [],
        'materialized_skills': [{
            'id': 'skill-api', 'name': 'api-compatibility', 'version': 3,
        }],
        'source_commit_sha': 'source-sha',
        'final_commit_sha': 'source-sha',
        'final_diff': 'diff --git a/a.py b/a.py',
        'changed_files': ['a.py'],
        'final_response': 'Implemented the change.',
        'error': None,
    }
    assert result.execution_context['runtime_artifacts'] == expected_artifacts
    assert activity_run_response(repository.document).payload == expected_artifacts

    committed = await service.continue_run(
        user_id='user-1', activity_id=activity.id, run_id='run-1',
        pipeline_run_id='pipeline-run-1', lease_token='lease-1',
        continuation_token='token-2', idempotency_key='commit-1',
        action='commit_if_allowed',
        result={
            'action': 'commit_if_allowed',
            'committed': True,
            'commit_sha': 'final-sha',
            'commit_message': 'feat: implement requested change',
        },
    )

    assert committed.execution_context['runtime_artifacts'] == {
        **expected_artifacts,
        'committed': True,
        'final_commit_sha': 'final-sha',
    }


@pytest.mark.asyncio
async def test_completed_codex_turn_requires_commit_message_when_allowed(
    tenant_service: TenantService,
) -> None:
    """An allowed Codex run cannot advance to commit without a proposed message."""

    service, repository, activity = _service(
        tenant_service=tenant_service,
        commit_mode='allow',
    )

    with pytest.raises(
        ActivityRunValidationError,
        match='result.commit_message.*must not be empty',
    ):
        await service.continue_run(
            user_id='user-1', activity_id=activity.id, run_id='run-1',
            pipeline_run_id='pipeline-run-1', lease_token='lease-1',
            continuation_token='token-1', idempotency_key='harness-1',
            action='run_harness',
            result=_harness_result(),
        )

    assert repository.transition_arguments is None


@pytest.mark.asyncio
async def test_completed_codex_turn_rejects_a_different_requested_model(
    tenant_service: TenantService,
) -> None:
    """A worker cannot replace the model frozen by the PipelineRun."""

    service, repository, activity = _service(
        tenant_service=tenant_service,
        commit_mode='allow',
    )

    with pytest.raises(
        ActivityRunValidationError,
        match='result.requested_model.*must match the frozen requested model',
    ):
        await service.continue_run(
            user_id='user-1', activity_id=activity.id, run_id='run-1',
            pipeline_run_id='pipeline-run-1', lease_token='lease-1',
            continuation_token='token-1', idempotency_key='harness-1',
            action='run_harness',
            result={
                **_harness_result(),
                'commit_message': 'feat: implement requested change',
                'requested_model': 'worker-local-model',
                'actual_model': 'worker-local-model',
            },
        )

    assert repository.transition_arguments is None


@pytest.mark.asyncio
async def test_forbidden_codex_commit_does_not_require_message(
    tenant_service: TenantService,
) -> None:
    """A commit-forbidden Codex run completes without a commit handoff."""

    service, _, activity = _service(
        tenant_service=tenant_service,
        commit_mode='forbid',
    )

    result = await service.continue_run(
        user_id='user-1', activity_id=activity.id, run_id='run-1',
        pipeline_run_id='pipeline-run-1', lease_token='lease-1',
        continuation_token='token-1', idempotency_key='harness-1',
        action='run_harness',
        result=_harness_result(),
    )

    assert result.status == 'completed'
    assert result.next_action == 'none'
    assert result.execution_context['runtime_artifacts']['completed'] is True
    assert result.execution_context['runtime_artifacts']['final_response'] == (
        'Implemented the change.'
    )
    assert result.execution_context['runtime_artifacts']['materialized_skills'] == [{
        'id': 'skill-api', 'name': 'api-compatibility', 'version': 3,
    }]


@pytest.mark.asyncio
async def test_failed_codex_turn_exposes_partial_observations(
    tenant_service: TenantService,
) -> None:
    """A failed Harness result remains available through the ActivityRun GET view."""

    service, repository, activity = _service(
        tenant_service=tenant_service,
        commit_mode='allow',
    )
    partial = {
        **_harness_result(),
        'completed': False,
        'actual_model': None,
        'exit_code': 17,
        'final_response': '',
        'usage': {'input_tokens': 10},
        'diagnostics': ['Codex failed.'],
        'error': 'Codex failed.',
    }

    failed = await service.continue_run(
        user_id='user-1', activity_id=activity.id, run_id='run-1',
        pipeline_run_id='pipeline-run-1', lease_token='lease-1',
        continuation_token='token-1', idempotency_key='harness-1',
        action='run_harness', result=partial,
    )

    assert failed.status == 'failed'
    payload = activity_run_response(repository.document).payload
    assert payload['completed'] is False
    assert payload['exit_code'] == 17
    assert payload['session_reference'] == 'thread-1'
    assert payload['usage'] == {'input_tokens': 10}
    assert payload['diagnostics'] == ['Codex failed.']
    assert payload['error'] == 'Codex failed.'


def _service(
    *,
    tenant_service: TenantService,
    commit_mode: str,
) -> tuple[ActivityRunService, _ActivityRunRepository, ActivityDocument]:
    """Build one pending Codex Activity checkpoint with a commit policy."""

    now = datetime(2026, 8, 31, tzinfo=UTC)
    activity = ActivityDocument(
        id='activity-1', name='Implement', description='Implement the task.',
        status='active', type='direct_loop', config={},
        created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
    )
    repository = _ActivityRunRepository(ActivityRunDocument(
        id='run-1', project_id='workspace-1', activity_id=activity.id,
        input='Implement.', status='in_progress', state='awaiting_harness',
        next_action='run_harness', iteration=1, token_revision=1,
        continuation_token='token-1',
        activity_snapshot={
            'flow': 'direct',
            'commit_mode': commit_mode,
            'requested_model': 'gpt-5-codex',
            'harness': {'kind': 'codex_cli', 'version': 'v1', 'config': {}},
        },
        execution_context={}, created_at=now, created_by='user-1', updated_at=now,
    ))
    return (
        ActivityRunService(
            repository=repository,
            activity_service=_ActivityService(activity),
            tenant_service=tenant_service,
            id_factory=lambda: 'unused',
            clock=lambda: now,
            token_factory=lambda: 'token-2',
        ),
        repository,
        activity,
    )


def _harness_result() -> dict[str, object]:
    """Build one complete normalized Codex observation."""

    return {
        'action': 'run_harness',
        'completed': True,
        'started_at': '2026-08-31T10:00:00+00:00',
        'completed_at': '2026-08-31T10:00:02+00:00',
        'duration_ms': 2000,
        'final_response': 'Implemented the change.',
        'requested_model': 'gpt-5-codex',
        'actual_model': 'gpt-5.1-codex',
        'reasoning_effort': 'high',
        'session_reference': 'thread-1',
        'usage': {'input_tokens': 10, 'reasoning_output_tokens': 3},
        'exit_code': 0,
        'diagnostics': [],
        'materialized_skills': [{
            'id': 'skill-api', 'name': 'api-compatibility', 'version': 3,
        }],
        'source_commit_sha': 'source-sha',
        'final_commit_sha': 'source-sha',
        'final_diff': 'diff --git a/a.py b/a.py',
        'changed_files': ['a.py'],
        'error': None,
    }
