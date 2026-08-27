"""Tests for Harness-aware Activity-run checkpoint transitions."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.app.models.activity import ActivityDocument
from src.app.models.activity_run import ActivityRunDocument
from src.app.models.pipeline import PipelineHarness
from src.app.models.user import UserDocument, UserSettings
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

    async def create(self, *, document: ActivityRunDocument) -> ActivityRunDocument:
        """Persist a newly created direct Activity run."""

        self.document = document
        return document

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


class _UserService:
    """Return one user with a configured default Harness."""

    def __init__(self, document: UserDocument) -> None:
        """Store the user returned by every lookup."""

        self._document = document

    async def get(self, **_arguments: object) -> UserDocument:
        """Return the configured user profile."""

        return self._document


class _ModelExecutionService:
    """Record model-selection requests and return one linked service."""

    def __init__(self) -> None:
        """Initialize the deterministic linked-service selection fixture."""

        self.calls: list[tuple[str, str, str]] = []

    async def select_linked_service(
        self,
        *,
        project_id: str,
        model_id: str,
        user_id: str,
    ) -> SimpleNamespace:
        """Record and return the linked service selected for a logical model."""

        self.calls.append((project_id, model_id, user_id))
        return SimpleNamespace(
            id='linked-service-selected',
            user_id=user_id,
        )


@pytest.mark.asyncio
async def test_create_inherits_user_default_harness(
    tenant_service: TenantService,
) -> None:
    """A direct Activity run freezes the user Harness when higher scopes are unset."""

    now = datetime(2026, 8, 24, tzinfo=UTC)
    activity = ActivityDocument(
        id='activity-1', name='Implement',
        description='Implement the requested change.', status='active', type='direct_loop',
        config={}, created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
    )
    repository = _ActivityRunRepository(ActivityRunDocument(
        id='existing', project_id='workspace-1', activity_id=activity.id,
        input='Ignored.', status='in_progress', state='awaiting_snapshot',
        next_action='collect_snapshot', iteration=1, token_revision=0,
        continuation_token='token', activity_snapshot={}, execution_context={},
        created_at=now, created_by='user-1', updated_at=now,
    ))
    service = ActivityRunService(
        repository=repository, activity_service=_ActivityService(activity),
        tenant_service=tenant_service, id_factory=lambda: 'run-1', clock=lambda: now,
        user_service=_UserService(UserDocument(  # type: ignore[arg-type]
            id='user-1', created_at=now, updated_at=now,
            settings=UserSettings(default_harness=PipelineHarness(kind='codex_cli')),
        )),
    )

    created = await service.create(
        user_id='user-1', activity_id=activity.id, input_text='Implement.',
    )

    assert created.activity_snapshot['harness'] == {
        'kind': 'codex_cli', 'version': 'v1', 'config': {},
    }


@pytest.mark.asyncio
async def test_create_louie_freezes_selected_service_for_effective_model(
    tenant_service: TenantService,
) -> None:
    """A Louie direct Activity resolves and freezes the User model default."""

    now = datetime(2026, 8, 24, tzinfo=UTC)
    activity = ActivityDocument(
        id='activity-1', name='Implement',
        description='Implement the requested change.', status='active', type='direct_loop',
        config={'agents': [{'persona_id': 'persona-1', 'role': 'generator'}]},
        created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
    )
    selector = _ModelExecutionService()
    service = ActivityRunService(
        repository=_ActivityRunRepository(ActivityRunDocument(
            id='existing', project_id='workspace-1', activity_id=activity.id,
            input='Ignored.', status='in_progress', state='awaiting_snapshot',
            next_action='collect_snapshot', iteration=1, token_revision=0,
            continuation_token='token', activity_snapshot={}, execution_context={},
            created_at=now, created_by='user-1', updated_at=now,
        )),
        activity_service=_ActivityService(activity), tenant_service=tenant_service,
        id_factory=lambda: 'run-1', clock=lambda: now,
        model_execution_service=selector,  # type: ignore[arg-type]
        user_service=_UserService(UserDocument(  # type: ignore[arg-type]
            id='user-1', created_at=now, updated_at=now,
            settings=UserSettings(default_model_id='gpt-5'),
        )),
    )

    created = await service.create(
        user_id='user-1', activity_id=activity.id, input_text='Implement.',
    )

    assert selector.calls == [('workspace-1', 'gpt-5', 'user-1')]
    assert created.activity_snapshot['agents'][0]['model_target'] == {
        'linked_service_id': 'linked-service-selected',
        'linked_service_user_id': 'user-1',
        'model_id': 'gpt-5',
    }


@pytest.mark.asyncio
async def test_create_rejects_louie_activity_without_effective_model(
    tenant_service: TenantService,
) -> None:
    """Louie cannot create a direct run when no agent or inherited model exists."""

    now = datetime(2026, 8, 24, tzinfo=UTC)
    activity = ActivityDocument(
        id='activity-1', name='Implement',
        description='Implement the requested change.', status='active', type='direct_loop',
        config={'agents': [{'persona_id': 'persona-1', 'role': 'generator'}]},
        created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
    )
    service = ActivityRunService(
        repository=_ActivityRunRepository(ActivityRunDocument(
            id='existing', project_id='workspace-1', activity_id=activity.id,
            input='Ignored.', status='in_progress', state='awaiting_snapshot',
            next_action='collect_snapshot', iteration=1, token_revision=0,
            continuation_token='token', activity_snapshot={}, execution_context={},
            created_at=now, created_by='user-1', updated_at=now,
        )),
        activity_service=_ActivityService(activity), tenant_service=tenant_service,
        id_factory=lambda: 'run-1', clock=lambda: now,
        model_execution_service=_ModelExecutionService(),  # type: ignore[arg-type]
    )

    with pytest.raises(
        Exception,
        match='louie execution requires a model_id',
    ):
        await service.create(
            user_id='user-1', activity_id=activity.id, input_text='Implement.',
        )


@pytest.mark.asyncio
async def test_create_codex_activity_does_not_select_api_managed_model(
    tenant_service: TenantService,
) -> None:
    """Codex keeps model selection external even when an agent declares a model."""

    now = datetime(2026, 8, 24, tzinfo=UTC)
    activity = ActivityDocument(
        id='activity-1', name='Implement',
        description='Implement the requested change.', status='active', type='direct_loop',
        config={'agents': [{'model_id': 'gpt-5', 'persona_id': 'persona-1', 'role': 'generator'}]},
        harness=PipelineHarness(kind='codex_cli'),
        created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
    )
    selector = _ModelExecutionService()
    service = ActivityRunService(
        repository=_ActivityRunRepository(ActivityRunDocument(
            id='existing', project_id='workspace-1', activity_id=activity.id,
            input='Ignored.', status='in_progress', state='awaiting_snapshot',
            next_action='collect_snapshot', iteration=1, token_revision=0,
            continuation_token='token', activity_snapshot={}, execution_context={},
            created_at=now, created_by='user-1', updated_at=now,
        )),
        activity_service=_ActivityService(activity), tenant_service=tenant_service,
        id_factory=lambda: 'run-1', clock=lambda: now,
        model_execution_service=selector,  # type: ignore[arg-type]
    )

    created = await service.create(
        user_id='user-1', activity_id=activity.id, input_text='Implement.',
    )

    assert selector.calls == []
    assert created.activity_snapshot['agents'][0]['model_id'] == 'gpt-5'
    assert 'model_target' not in created.activity_snapshot['agents'][0]


@pytest.mark.asyncio
async def test_collect_snapshot_routes_frozen_codex_direct_loop_to_harness(
    tenant_service: TenantService,
) -> None:
    """A Codex Pipeline child requests a local Harness turn without API generation."""

    now = datetime(2026, 8, 24, tzinfo=UTC)
    activity = ActivityDocument(
        id='activity-1', name='Implement',
        description='Implement the requested change.', status='active', type='direct_loop',
        config={}, created_at=now, created_by='user-1', updated_at=now, updated_by='user-1',
    )
    document = ActivityRunDocument(
        id='run-1', project_id='workspace-1', activity_id=activity.id,
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
