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
            'action': 'run_harness',
            'completed': True,
            'final_response': 'Implemented the change.',
            'commit_message': 'feat: implement requested change',
        },
    )

    assert result.next_action == 'commit_if_allowed'
    assert result.execution_context['runtime_artifacts'] == {
        'commit_message': 'feat: implement requested change',
    }
    assert activity_run_response(repository.document).payload == {
        'commit_message': 'feat: implement requested change',
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
            result={'action': 'run_harness', 'completed': True},
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
        result={'action': 'run_harness', 'completed': True},
    )

    assert result.status == 'completed'
    assert result.next_action == 'none'
    assert 'runtime_artifacts' not in result.execution_context


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
