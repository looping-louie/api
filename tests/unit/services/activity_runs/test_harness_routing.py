"""Tests for Harness-aware Activity-run checkpoint transitions."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from src.app.models.activity import ActivityDocument
from src.app.models.activity_run import ActivityRunDocument
from src.app.services.activity_runs.service import ActivityRunService
from src.app.services.shared.tenant import TenantService


class _ActivityService:
    """Return one active direct-loop Activity for the transition test."""

    def __init__(self, activity: ActivityDocument) -> None:
        """Store the Activity returned for every requested execution."""

        self._activity = activity

    async def get(self, **_arguments: object) -> ActivityDocument:
        """Return the active Activity belonging to the frozen run."""

        return self._activity


class _ActivityRunRepository:
    """Persist one ActivityRun document and record its next transition."""

    def __init__(self, document: ActivityRunDocument) -> None:
        """Store the current ActivityRun and initialize the transition log."""

        self.document = document
        self.transition_arguments: dict[str, object] | None = None

    async def get(self, **_arguments: object) -> ActivityRunDocument:
        """Return the stored ActivityRun."""

        return self.document

    async def has_active_pipeline_lease(self, **_arguments: object) -> bool:
        """Authorize the fixture's Pipeline-owned continuation."""

        return True

    async def transition(self, **arguments: object) -> ActivityRunDocument:
        """Record and apply the requested state transition."""

        self.transition_arguments = arguments
        self.document = replace(
            self.document,
            status=str(arguments['status']),
            state=str(arguments['state']),
            next_action=str(arguments['next_action']),
            continuation_token=arguments['next_continuation_token'],
            execution_context=dict(arguments['execution_context']),
        )
        return self.document


@pytest.mark.asyncio
async def test_collect_snapshot_routes_frozen_codex_direct_loop_to_harness(
    tenant_service: TenantService,
) -> None:
    """A Codex Pipeline child requests a local Harness turn without API generation."""

    now = datetime(2026, 8, 24, tzinfo=UTC)
    activity = ActivityDocument(
        id='activity-1', workspace_id='workspace-1', name='Implement',
        description='Implement the requested change.', status='active', type='direct_loop',
        config={}, created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
    )
    document = ActivityRunDocument(
        id='run-1', workspace_id='workspace-1', activity_id=activity.id,
        input='Create a file.', status='in_progress', state='awaiting_snapshot',
        next_action='collect_snapshot', iteration=1, token_revision=0,
        continuation_token='token-1',
        activity_snapshot={
            'flow': 'direct',
            'executor': 'runtime',
            'harness': {'kind': 'codex_cli', 'version': 'v1', 'config': {}},
        },
        execution_context={}, created_at=now, created_by='user-1', updated_at=now,
    )
    repository = _ActivityRunRepository(document)
    service = ActivityRunService(
        repository=repository, activity_service=_ActivityService(activity),
        tenant_service=tenant_service, id_factory=lambda: 'unused', clock=lambda: now,
        token_factory=lambda: 'token-2',
    )

    result = await service.continue_run(
        user_id='user-1', activity_id=activity.id, run_id=document.id,
        pipeline_run_id='pipeline-run-1', lease_token='lease-1',
        continuation_token='token-1', idempotency_key='snapshot-1',
        action='collect_snapshot',
        result={
            'action': 'collect_snapshot',
            'repo_context': 'Repository context.',
            'workspace_metadata': {'workspace_path': '/checkout', 'source_commit_sha': 'abc'},
            'constitution': '',
            'project_profile': {},
        },
    )

    assert result.state == 'awaiting_harness'
    assert result.next_action == 'run_harness'
    assert result.continuation_token == 'token-2'
    assert result.execution_context['repo_context'] == 'Repository context.'