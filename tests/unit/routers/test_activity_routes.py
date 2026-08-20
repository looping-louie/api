"""HTTP contract tests for activity routes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime
from itertools import count
from typing import cast

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.activity import ActivityController
from src.app.controllers.activity_run import ActivityRunController
from src.app.models.activity_run import ActivityRunDocument
from src.app.routers.activities import router as activities_router
from src.app.services.activity_runs import ActivityRunService
from src.app.services.activities.service import ActivityService
from src.app.services.models.availability import ModelNotFoundError
from src.app.services.model_execution import ModelExecutionResult
from src.app.catalogs.providers import ProviderId
from src.app.services.personas import PersonaLinkedServiceSelection
from src.app.services.shared.reference_resolver import ReferenceResolver
from src.app.services.shared.tenant import TenantService
from src.app.utils.http import register_exception_handlers
from tests.fakes.activity_repository import FakeActivityRepository
from tests.fakes.persona_linked_service_selection_repository import (
    FakePersonaLinkedServiceSelectionRepository,
)
from tests.fakes.reference_repository import FakeReferenceRepository


class FakeActivityRunRepository:
    """Store activity-owned runs for Activity execution route tests."""

    def __init__(self) -> None:
        """Initialize an empty activity-owned run collection."""

        self.documents: dict[str, ActivityRunDocument] = {}

    async def create(self, *, document: ActivityRunDocument) -> ActivityRunDocument:
        """Store one newly created run."""

        self.documents[document.id] = document
        return document

    async def get(self, *, workspace_id: str, activity_id: str, run_id: str) -> ActivityRunDocument | None:
        """Return a run only for its parent activity."""

        document = self.documents.get(run_id)
        return document if document is not None and document.workspace_id == workspace_id and document.activity_id == activity_id else None

    async def list(self, *, workspace_id: str, activity_id: str, offset: int, limit: int) -> tuple[list[ActivityRunDocument], int]:
        """Return a deterministic page for one activity."""

        values = [document for document in self.documents.values() if document.workspace_id == workspace_id and document.activity_id == activity_id]
        return values[offset:offset + limit], len(values)

    async def has_active_pipeline_lease(self, **_: object) -> bool:
        """Allow standalone route-fixture activity runs to continue."""

        return True

    async def transition(self, *, workspace_id: str, activity_id: str, run_id: str, continuation_token: str, idempotency_key: str, expected_action: str, status: str, state: str, next_action: str, next_continuation_token: str | None, execution_context: dict[str, object], updated_at: datetime, iteration: int | None = None, pipeline_run_id: str | None = None, lease_token: str | None = None) -> ActivityRunDocument:
        """Advance the snapshot checkpoint for the in-memory route fixture."""

        del idempotency_key, pipeline_run_id, lease_token
        current = self.documents[run_id]
        assert current.workspace_id == workspace_id and current.activity_id == activity_id
        assert current.continuation_token == continuation_token and current.next_action == expected_action
        updated = ActivityRunDocument(id=current.id, workspace_id=current.workspace_id, activity_id=current.activity_id, input=current.input, status=cast(object, status), state=cast(object, state), next_action=cast(object, next_action), iteration=iteration or current.iteration, token_revision=current.token_revision + 1, continuation_token=next_continuation_token, activity_snapshot=current.activity_snapshot, execution_context=execution_context, created_at=current.created_at, created_by=current.created_by, updated_at=updated_at)
        self.documents[run_id] = updated
        return updated


class MissingModelExecutionService:
    """Raise the API-owned model resolution error observed by runtime workers."""

    async def execute(self, **_: object) -> object:
        """Reject execution because the configured model is absent from the catalog."""

        raise ModelNotFoundError(model_id='missing-model')


class NoCommitModelExecutionService:
    """Return a valid operation plan without a commit message."""

    async def execute(self, **_: object) -> ModelExecutionResult:
        """Return the file operation required by the activity checkpoint."""

        return ModelExecutionResult(
            text=(
                '{"operations":[{"operation":"replace_text","path":"index.html",'
                '"old_content":"Old title","new_content":"New title"}]}'
            ),
            provider_id=ProviderId.TOGETHER,
            model_id='model-1',
            input_tokens=1,
            output_tokens=1,
            duration_ms=1,
        )


class EmptyInstructionLibraryService:
    """Provide no instruction library for generation route tests."""

    async def load(self, **_: object) -> None:
        """Return no optional instruction snapshot."""

        return None


def build_client(
    *,
    tenant_service: TenantService,
    persona_selection_repository: FakePersonaLinkedServiceSelectionRepository | None = None,
    reference_repository: FakeReferenceRepository | None = None,
    model_execution_service: object | None = None,
) -> TestClient:
    """Build an authenticated activity application with in-memory storage."""

    identifiers = count(1)
    service = ActivityService(
        repository=FakeActivityRepository(),
        tenant_service=tenant_service,
        reference_resolver=ReferenceResolver(
            repository=reference_repository or FakeReferenceRepository(),
        ),
        persona_linked_service_selection_repository=(
            persona_selection_repository
            or FakePersonaLinkedServiceSelectionRepository()
        ),
        id_factory=lambda: f'activity-{next(identifiers)}',
        clock=lambda: datetime(2026, 8, 12, tzinfo=UTC),
    )
    app = FastAPI()
    app.state.activity_controller = ActivityController(activity_service=service)
    activity_run_repository = FakeActivityRunRepository()
    app.state.activity_run_controller = ActivityRunController(activity_run_service=ActivityRunService(
        repository=cast(object, activity_run_repository),
        activity_service=service,
        tenant_service=tenant_service, id_factory=lambda: f'run-{next(identifiers)}',
        token_factory=lambda: 'continuation-token', clock=lambda: datetime(2026, 8, 12, tzinfo=UTC),
        model_execution_service=cast(object, model_execution_service),
        instruction_library_service=(
            EmptyInstructionLibraryService()
            if model_execution_service is not None
            else None
        ),
    ))
    app.state.activity_run_repository = activity_run_repository

    @app.middleware('http')
    async def add_authenticated_user(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Inject the actor required by route dependencies."""

        request.state.user_id = 'user-1'
        return await call_next(request)

    register_exception_handlers(app)
    app.include_router(activities_router, prefix='/api/v1')
    return TestClient(app)


def direct_loop_payload() -> dict[str, object]:
    """Return one valid direct loop activity body."""

    return {
        'name': 'Implementation_activity',
        'description': 'Produce a change.',
        'type': 'direct_loop',
        'config': {
            'stop_conditions': {'max_tokens': 100},
            'agents': [{'model_id': 'model-1', 'persona_id': 'persona-1', 'role': 'generator'}],
            'output_contract': {'type': 'text', 'description': 'A result.'},
        },
    }


def roundtable_loop_payload() -> dict[str, object]:
    """Return one valid roundtable loop activity body."""

    return {
        'name': 'Roundtable_activity',
        'description': 'Reach a shared decision.',
        'type': 'roundtable_loop',
        'config': {
            'stop_conditions': {'max_tokens': 100},
            'agents': [
                {'model_id': 'model-1', 'persona_id': 'persona-1', 'role': 'generator'},
                {'model_id': 'model-2', 'persona_id': 'persona-2', 'role': 'generator'},
                {'model_id': 'model-3', 'persona_id': 'persona-3', 'role': 'aggregator'},
            ],
            'output_contract': {'type': 'text', 'description': 'A result.'},
        },
    }


def test_activity_rest_crud_changelog_and_type_directed_configs(tenant_service: TenantService) -> None:
    """Create, read, update, audit, delete, and validate both activity types."""

    client = build_client(tenant_service=tenant_service)
    created = client.post('/api/v1/activities', json=direct_loop_payload())
    assert created.status_code == 201
    activity_id = created.json()['id']
    assert created.json()['type'] == 'direct_loop'
    assert 'type' not in created.json()['config']

    quiz = client.post('/api/v1/activities', json={
        'name': 'Review_quiz', 'description': 'Answer the questions.',
        'type': 'quiz',
        'config': {'quiz': {'questions': []}},
    })
    refinement = client.post('/api/v1/activities', json={
        'name': 'Refine_change', 'description': 'Review and refine a change.',
        'type': 'refinement_loop',
        'config': {
            'stop_conditions': {'max_tokens': 100},
            'agents': [
                {'model_id': 'model-1', 'persona_id': 'persona-1', 'role': 'generator'},
                {'model_id': 'model-2', 'persona_id': 'persona-2', 'role': 'reviewer'},
            ],
            'output_contract': {'type': 'text', 'description': 'A result.'},
        },
    })
    roundtable = client.post(
        '/api/v1/activities',
        json=roundtable_loop_payload(),
    )
    patched = client.patch(f'/api/v1/activities/{activity_id}', json={'status': 'disabled'})
    changelog = client.get(f'/api/v1/activities/{activity_id}/changelog')
    deleted = client.delete(f'/api/v1/activities/{activity_id}')
    retained = client.get(f'/api/v1/activities/{activity_id}/changelog')
    invalid_quiz = client.post('/api/v1/activities', json={
        'name': 'Invalid', 'description': '',
        'type': 'quiz',
        'config': {},
    })
    legacy_config_type = client.post('/api/v1/activities', json={
        **direct_loop_payload(),
        'config': {
            **direct_loop_payload()['config'],
            'type': 'direct_loop',
        },
    })

    assert quiz.status_code == 201
    assert quiz.json()['type'] == 'quiz'
    assert quiz.json()['config']['quiz'] == {'questions': []}
    assert refinement.status_code == 201
    assert refinement.json()['type'] == 'refinement_loop'
    assert roundtable.status_code == 201
    assert roundtable.json()['type'] == 'roundtable_loop'
    assert patched.json()['status'] == 'disabled'
    assert changelog.json()['items'][0]['change_type'] == 'disabled'
    assert changelog.json()['items'][0]['diff']['status'] == 'disabled'
    assert deleted.json() == {'deleted': True}
    assert retained.status_code == 200
    assert retained.json()['items'][0]['change_type'] == 'deleted'
    assert invalid_quiz.status_code == 422
    assert legacy_config_type.status_code == 422
    assert 'error' in legacy_config_type.json()


def test_activity_rejects_agent_without_model_or_persona_selection(
    tenant_service: TenantService,
) -> None:
    """Activities require one execution source for every loop agent."""

    reference_repository = FakeReferenceRepository()
    reference_repository.seed(
        workspace_id='workspace-1',
        resource_type='persona',
        resource_id='persona-1',
        value={'id': 'persona-1'},
    )
    client = build_client(
        tenant_service=tenant_service,
        reference_repository=reference_repository,
    )
    payload = direct_loop_payload()
    payload['config']['agents'][0].pop('model_id')

    response = client.post('/api/v1/activities', json=payload)

    assert response.status_code == 422
    assert response.json()['error']['code'] == 'activity_validation_error'
    assert response.json()['error']['details']['reason'].endswith(
        'Persona has no linked-service selection'
    )


def test_activity_rejects_unavailable_persona_before_selection_check(
    tenant_service: TenantService,
) -> None:
    """Selection-only agents resolve Personas before validating selections."""

    client = build_client(tenant_service=tenant_service)
    payload = direct_loop_payload()
    payload['config']['agents'][0].pop('model_id')

    response = client.post('/api/v1/activities', json=payload)

    assert response.status_code == 404
    assert response.json()['error']['code'] == 'referenced_resource_not_found'


@pytest.mark.asyncio
async def test_activity_allows_agent_without_model_for_persona_selection(
    tenant_service: TenantService,
) -> None:
    """An Activity agent may rely on its Persona linked-service selection."""

    selection_repository = FakePersonaLinkedServiceSelectionRepository()
    reference_repository = FakeReferenceRepository()
    reference_repository.seed(
        workspace_id='workspace-1',
        resource_type='persona',
        resource_id='persona-1',
        value={'id': 'persona-1'},
    )
    await selection_repository.replace_for_persona(
        persona_id='persona-1',
        selection=PersonaLinkedServiceSelection(
            linked_service_id='linked-service-1',
            model_id='model-1',
        ),
    )
    client = build_client(
        tenant_service=tenant_service,
        persona_selection_repository=selection_repository,
        reference_repository=reference_repository,
    )
    payload = direct_loop_payload()
    payload['config']['agents'][0].pop('model_id')

    response = client.post('/api/v1/activities', json=payload)

    assert response.status_code == 201
    assert response.json()['config']['agents'][0]['model_id'] is None


@pytest.mark.asyncio
async def test_activity_rejects_selection_for_persona_outside_workspace(
    tenant_service: TenantService,
) -> None:
    """Selection-only agents cannot reference Personas outside their workspace."""

    selection_repository = FakePersonaLinkedServiceSelectionRepository()
    await selection_repository.replace_for_persona(
        persona_id='persona-1',
        selection=PersonaLinkedServiceSelection(
            linked_service_id='linked-service-1',
            model_id='model-1',
        ),
    )
    reference_repository = FakeReferenceRepository()
    reference_repository.seed(
        workspace_id='workspace-other',
        resource_type='persona',
        resource_id='persona-1',
        value={'id': 'persona-1'},
    )
    client = build_client(
        tenant_service=tenant_service,
        persona_selection_repository=selection_repository,
        reference_repository=reference_repository,
    )
    payload = direct_loop_payload()
    payload['config']['agents'][0].pop('model_id')

    response = client.post('/api/v1/activities', json=payload)

    assert response.status_code == 404
    assert response.json()['error']['code'] == 'referenced_resource_not_found'


def test_direct_loop_requires_a_generator_agent(
    tenant_service: TenantService,
) -> None:
    """Direct loops reject configurations that cannot generate an operation plan."""

    client = build_client(tenant_service=tenant_service)
    response = client.post(
        '/api/v1/activities',
        json={
            **direct_loop_payload(),
            'config': {
                **direct_loop_payload()['config'],
                'agents': [],
            },
        },
    )

    assert response.status_code == 422
    assert response.json()['error']['code'] == 'request_validation_error'


@pytest.mark.parametrize(
    'name',
    [
        '-invalid',
        '.invalid',
        'invalid+name',
        'invalid?name',
        'invalid/name',
        'invalid<name',
        'invalid>name',
        'invalid*name',
        'invalid%name',
        'invalid&name',
        'invalid:name',
        'invalid name',
        'a' * 141,
    ],
)
def test_activity_rejects_invalid_names(
    tenant_service: TenantService,
    name: str,
) -> None:
    """Activity names follow the shared resource-name contract."""

    client = build_client(tenant_service=tenant_service)
    response = client.post(
        '/api/v1/activities',
        json={**direct_loop_payload(), 'name': name},
    )

    assert response.status_code == 422
    assert response.json()['error']['code'] == 'request_validation_error'


def test_activity_accepts_maximum_length_name(
    tenant_service: TenantService,
) -> None:
    """Activity names may contain exactly 140 valid characters."""

    client = build_client(tenant_service=tenant_service)
    response = client.post(
        '/api/v1/activities',
        json={**direct_loop_payload(), 'name': 'a' * 140},
    )

    assert response.status_code == 201


def test_loop_activities_reject_invalid_role_combinations(
    tenant_service: TenantService,
) -> None:
    """Activity schemas reject roles forbidden by each loop type."""

    client = build_client(tenant_service=tenant_service)
    invalid_payloads = [
        {
            **direct_loop_payload(),
            'config': {
                **direct_loop_payload()['config'],
                'agents': [
                    {'model_id': 'model-1', 'persona_id': 'persona-1', 'role': 'generator'},
                    {'model_id': 'model-2', 'persona_id': 'persona-2', 'role': 'reviewer'},
                ],
            },
        },
        {
            **roundtable_loop_payload(),
            'config': {
                **roundtable_loop_payload()['config'],
                'agents': [
                    *roundtable_loop_payload()['config']['agents'],
                    {'model_id': 'model-4', 'persona_id': 'persona-4', 'role': 'reviewer'},
                ],
            },
        },
        {
            'name': 'Invalid refinement',
            'description': 'Reject aggregation.',
            'type': 'refinement_loop',
            'config': {
                'stop_conditions': {'max_tokens': 100},
                'agents': [
                    {'model_id': 'model-1', 'persona_id': 'persona-1', 'role': 'generator'},
                    {'model_id': 'model-2', 'persona_id': 'persona-2', 'role': 'reviewer'},
                    {'model_id': 'model-3', 'persona_id': 'persona-3', 'role': 'aggregator'},
                ],
                'output_contract': {'type': 'text', 'description': 'A result.'},
            },
        },
    ]

    for payload in invalid_payloads:
        response = client.post('/api/v1/activities', json=payload)
        assert response.status_code == 422
        assert response.json()['error']['code'] == 'request_validation_error'


def test_activity_creates_approval_without_a_human_gate_wrapper(
    tenant_service: TenantService,
) -> None:
    """Approval is a top-level activity type with its own config shape."""

    client = build_client(tenant_service=tenant_service)

    created = client.post('/api/v1/activities', json={
        'name': 'Release_approval',
        'description': 'Approve the release.',
        'type': 'approval',
        'config': {},
    })

    assert created.status_code == 201
    assert created.json()['type'] == 'approval'
    assert created.json()['config'] == {}


def test_activity_rejects_an_invalid_top_level_type(
    tenant_service: TenantService,
) -> None:
    """Unsupported types use the standard request-validation envelope."""

    client = build_client(tenant_service=tenant_service)

    response = client.post(
        '/api/v1/activities',
        json={
            'name': 'Invalid activity',
            'description': 'Reject unsupported types.',
            'type': 'unsupported',
            'config': {},
        },
    )

    assert response.status_code == 422
    assert response.json()['error']['code'] == 'request_validation_error'


def test_activity_rejects_legacy_title_field(
    tenant_service: TenantService,
) -> None:
    """Activity requests require the public name field."""

    client = build_client(tenant_service=tenant_service)
    response = client.post(
        '/api/v1/activities',
        json={
            'title': 'Legacy title',
            'description': 'Reject the retired field.',
            'type': 'approval',
            'config': {},
        },
    )

    assert response.status_code == 422
    assert response.json()['error']['code'] == 'request_validation_error'


def test_activity_patch_rejects_legacy_nested_config_type(
    tenant_service: TenantService,
) -> None:
    """Nested type fields are not accepted in an immutable config update."""

    client = build_client(tenant_service=tenant_service)
    created = client.post('/api/v1/activities', json=direct_loop_payload())

    response = client.patch(
        f"/api/v1/activities/{created.json()['id']}",
        json={
            'config': {
                'type': 'direct_loop',
                'stop_conditions': {'max_tokens': 100},
                'agents': [],
                'output_contract': {
                    'type': 'text',
                    'description': 'A result.',
                },
            },
        },
    )

    assert response.status_code == 422
    assert response.json()['error']['code'] == 'activity_validation_error'
    assert response.json()['error']['details']['field'] == 'config'


def test_activity_run_routes_support_runtime_and_human_executors(tenant_service: TenantService) -> None:
    """Active Activities create runs for their assigned runtime or human executor."""

    client = build_client(tenant_service=tenant_service)
    activity_id = client.post('/api/v1/activities', json=direct_loop_payload()).json()['id']
    created = client.post(f'/api/v1/activities/{activity_id}/runs', json={'input': 'Create a file.'})
    roundtable_id = client.post(
        '/api/v1/activities',
        json=roundtable_loop_payload(),
    ).json()['id']
    roundtable_run = client.post(
        f'/api/v1/activities/{roundtable_id}/runs',
        json={'input': 'Create a file.'},
    )
    run_id = created.json()['id']
    listed = client.get(f'/api/v1/activities/{activity_id}/runs')
    fetched = client.get(f'/api/v1/activities/{activity_id}/runs/{run_id}')
    continued = client.post(f'/api/v1/activities/{activity_id}/runs/{run_id}/continue', json={
        'continuation_token': created.json()['continuation_token'], 'idempotency_key': 'snapshot-1',
        'result': {'action': 'collect_snapshot', 'repo_context': 'Repository context.', 'workspace_metadata': {'workspace_path': '/project', 'source_commit_sha': 'abc'}, 'constitution': '', 'project_profile': {'source_file_count': 1, 'approximate_source_chars': 1, 'extension_counts': {}, 'top_level_entries': [], 'markers': {'nuxt': False, 'package_json': False, 'fastapi': True, 'docker': False, 'tests': True}}},
    })
    approval = client.post('/api/v1/activities', json={'name': 'Approval', 'description': '', 'type': 'approval', 'config': {}})
    human_run = client.post(f"/api/v1/activities/{approval.json()['id']}/runs", json={'input': 'Approve it.'})
    human_decision = client.post(
        f"/api/v1/activities/{approval.json()['id']}/runs/{human_run.json()['id']}/continue",
        json={
            'continuation_token': human_run.json()['continuation_token'],
            'idempotency_key': 'approval-1',
            'result': {
                'action': 'submit_human_decision',
                'decision': 'approved',
                'comment': 'Approved by the reviewer.',
            },
        },
    )
    refinement = client.post('/api/v1/activities', json={
        'name': 'Refinement', 'description': '', 'type': 'refinement_loop',
        'config': {
            'stop_conditions': {'max_tokens': 100},
                'agents': [
                    {'model_id': 'model-1', 'persona_id': 'persona-1', 'role': 'generator'},
                    {'model_id': 'model-2', 'persona_id': 'persona-2', 'role': 'reviewer'},
                ],
            'output_contract': {'type': 'text', 'description': 'A result.'},
        },
    })
    refinement_run = client.post(f"/api/v1/activities/{refinement.json()['id']}/runs", json={'input': 'No run.'})
    client.patch(f'/api/v1/activities/{activity_id}', json={'status': 'disabled'})
    disabled = client.post(f'/api/v1/activities/{activity_id}/runs', json={'input': 'No run.'})

    assert created.status_code == 201
    assert created.json()['activity_id'] == activity_id
    assert roundtable_run.status_code == 201
    assert roundtable_run.json()['activity_id'] == roundtable_id
    assert listed.json()['items'][0]['id'] == run_id
    assert fetched.json()['id'] == run_id
    assert continued.json()['state'] == 'awaiting_generation'
    assert human_run.status_code == 201
    assert human_run.json()['state'] == 'awaiting_human_decision'
    assert human_decision.json()['status'] == 'completed'
    assert refinement_run.status_code == 201
    assert refinement_run.json()['activity_id'] == refinement.json()['id']
    assert disabled.status_code == 409
    assert disabled.json()['error']['code'] == 'activity_run_unavailable'


def test_activity_checkpoint_marks_missing_model_generation_failed(
    tenant_service: TenantService,
) -> None:
    """A missing API model creates a terminal Activity result instead of a retryable claim."""

    client = build_client(
        tenant_service=tenant_service,
        model_execution_service=MissingModelExecutionService(),
    )
    activity_id = client.post('/api/v1/activities', json=direct_loop_payload()).json()['id']
    created = client.post(
        f'/api/v1/activities/{activity_id}/runs',
        json={'input': 'Change a title.'},
    )

    continued = client.post(
        f'/api/v1/activities/{activity_id}/runs/{created.json()["id"]}/continue',
        json={
            'continuation_token': created.json()['continuation_token'],
            'idempotency_key': 'snapshot-missing-model',
            'result': {
                'action': 'collect_snapshot',
                'repo_context': 'Repository context.',
                'workspace_metadata': {
                    'workspace_path': '/project',
                    'source_commit_sha': 'abc',
                },
                'constitution': '',
                'project_profile': {
                    'source_file_count': 1,
                    'approximate_source_chars': 1,
                    'extension_counts': {},
                    'top_level_entries': [],
                    'markers': {
                        'nuxt': False,
                        'package_json': False,
                        'fastapi': True,
                        'docker': False,
                        'tests': True,
                    },
                },
            },
        },
    )

    assert continued.status_code == 200
    assert continued.json()['status'] == 'failed'
    assert continued.json()['state'] == 'failed'
    assert continued.json()['next_action'] == 'none'
    assert continued.json()['continuation_token'] is None
    persisted = client.app.state.activity_run_repository.documents[created.json()['id']]
    assert persisted.execution_context['failure'] == {
        'source': 'api',
        'type': 'ModelNotFoundError',
        'message': "Model 'missing-model' was not found.",
    }


def test_forbidden_commit_activity_completes_after_operations(
    tenant_service: TenantService,
) -> None:
    """A forbid snapshot completes after apply without exposing a commit action."""

    client = build_client(
        tenant_service=tenant_service,
        model_execution_service=NoCommitModelExecutionService(),
    )
    activity_id = client.post('/api/v1/activities', json=direct_loop_payload()).json()['id']
    created = client.post(
        f'/api/v1/activities/{activity_id}/runs',
        json={'input': 'Change a title without committing.'},
    ).json()
    repository = client.app.state.activity_run_repository
    repository.documents[created['id']] = replace(
        repository.documents[created['id']],
        activity_snapshot={
            **repository.documents[created['id']].activity_snapshot,
            'commit_mode': 'forbid',
        },
    )

    generated = client.post(
        f'/api/v1/activities/{activity_id}/runs/{created["id"]}/continue',
        json={
            'continuation_token': created['continuation_token'],
            'idempotency_key': 'no-commit-snapshot',
            'result': {
                'action': 'collect_snapshot',
                'repo_context': 'Repository context.',
                'workspace_metadata': {
                    'workspace_path': '/project',
                    'source_commit_sha': 'abc',
                },
                'constitution': '',
                'project_profile': {
                    'source_file_count': 1,
                    'approximate_source_chars': 1,
                    'extension_counts': {},
                    'top_level_entries': [],
                    'markers': {
                        'nuxt': False,
                        'package_json': False,
                        'fastapi': True,
                        'docker': False,
                        'tests': True,
                    },
                },
            },
        },
    ).json()
    completed = client.post(
        f'/api/v1/activities/{activity_id}/runs/{created["id"]}/continue',
        json={
            'continuation_token': generated['continuation_token'],
            'idempotency_key': 'no-commit-apply',
            'result': {'action': 'apply_operations', 'applied': True},
        },
    )

    assert generated['next_action'] == 'apply_operations'
    assert completed.status_code == 200
    assert completed.json()['status'] == 'completed'
    assert completed.json()['state'] == 'completed'
    assert completed.json()['next_action'] == 'none'
    assert completed.json()['continuation_token'] is None
