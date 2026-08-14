"""HTTP contract tests for activity routes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from itertools import count
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.activity import ActivityController
from src.app.controllers.loop_run import LoopRunController
from src.app.models.loop_run import LoopRunDocument
from src.app.routers.activities import router as activities_router
from src.app.services.loop_runs import LoopRunService
from src.app.services.loops.service import LoopService
from src.app.services.activities.service import ActivityService
from src.app.services.shared.tenant import TenantService
from src.app.utils.http import register_exception_handlers
from tests.fakes.activity_repository import FakeActivityRepository


class FakeActivityRunRepository:
    """Store activity-owned runs for Activity execution route tests."""

    def __init__(self) -> None:
        """Initialize an empty activity-owned run collection."""

        self.documents: dict[str, LoopRunDocument] = {}

    async def create(self, *, document: LoopRunDocument) -> LoopRunDocument:
        """Store one newly created run."""

        self.documents[document.id] = document
        return document

    async def get_for_activity(self, *, workspace_id: str, activity_id: str, run_id: str) -> LoopRunDocument | None:
        """Return a run only for its parent activity."""

        document = self.documents.get(run_id)
        return document if document is not None and document.workspace_id == workspace_id and document.activity_id == activity_id else None

    async def list_for_activity(self, *, workspace_id: str, activity_id: str, offset: int, limit: int) -> tuple[list[LoopRunDocument], int]:
        """Return a deterministic page for one activity."""

        values = [document for document in self.documents.values() if document.workspace_id == workspace_id and document.activity_id == activity_id]
        return values[offset:offset + limit], len(values)

    async def transition_for_activity(self, *, workspace_id: str, activity_id: str, run_id: str, continuation_token: str, idempotency_key: str, expected_action: str, status: str, state: str, next_action: str, next_continuation_token: str | None, execution_context: dict[str, object], updated_at: datetime, iteration: int | None = None) -> LoopRunDocument:
        """Advance the snapshot checkpoint for the in-memory route fixture."""

        current = self.documents[run_id]
        assert current.workspace_id == workspace_id and current.activity_id == activity_id
        assert current.continuation_token == continuation_token and current.next_action == expected_action
        updated = LoopRunDocument(id=current.id, workspace_id=current.workspace_id, loop_id=current.loop_id, input=current.input, status=status, state=cast(object, state), next_action=cast(object, next_action), iteration=iteration or current.iteration, token_revision=current.token_revision + 1, continuation_token=next_continuation_token, loop_snapshot=current.loop_snapshot, execution_context=execution_context, created_at=current.created_at, created_by=current.created_by, updated_at=updated_at, activity_id=current.activity_id)
        self.documents[run_id] = updated
        return updated


def build_client(*, tenant_service: TenantService) -> TestClient:
    """Build an authenticated activity application with in-memory storage."""

    identifiers = count(1)
    service = ActivityService(
        repository=FakeActivityRepository(),
        tenant_service=tenant_service,
        id_factory=lambda: f'activity-{next(identifiers)}',
        clock=lambda: datetime(2026, 8, 12, tzinfo=UTC),
    )
    app = FastAPI()
    app.state.activity_controller = ActivityController(activity_service=service)
    app.state.loop_run_controller = LoopRunController(loop_run_service=LoopRunService(
        repository=cast(object, FakeActivityRunRepository()),
        loop_service=cast(LoopService, object()), activity_service=service,
        tenant_service=tenant_service, id_factory=lambda: f'run-{next(identifiers)}',
        token_factory=lambda: 'continuation-token', clock=lambda: datetime(2026, 8, 12, tzinfo=UTC),
    ))

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
        'name': 'Implementation activity',
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
        'name': 'Roundtable activity',
        'description': 'Reach a shared decision.',
        'type': 'roundtable_loop',
        'config': {
            'stop_conditions': {'max_tokens': 100},
            'agents': [],
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
        'name': 'Review quiz', 'description': 'Answer the questions.',
        'type': 'quiz',
        'config': {'quiz': {'questions': []}},
    })
    refinement = client.post('/api/v1/activities', json={
        'name': 'Refine change', 'description': 'Review and refine a change.',
        'type': 'refinement_loop',
        'config': {
            'stop_conditions': {'max_tokens': 100},
            'agents': [],
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


def test_activity_creates_approval_without_a_human_gate_wrapper(
    tenant_service: TenantService,
) -> None:
    """Approval is a top-level activity type with its own config shape."""

    client = build_client(tenant_service=tenant_service)

    created = client.post('/api/v1/activities', json={
        'name': 'Release approval',
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


def test_activity_loop_run_routes_scope_runs_and_reject_non_executable_activities(tenant_service: TenantService) -> None:
    """Only active loop activities create, read, and advance their own runs."""

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
    mismatch = client.post(f"/api/v1/activities/{approval.json()['id']}/runs", json={'input': 'No run.'})
    refinement = client.post('/api/v1/activities', json={
        'name': 'Refinement', 'description': '', 'type': 'refinement_loop',
        'config': {
            'stop_conditions': {'max_tokens': 100},
            'agents': [],
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
    assert mismatch.status_code == 409
    assert mismatch.json()['error']['code'] == 'activity_run_unavailable'
    assert refinement_run.status_code == 409
    assert refinement_run.json()['error']['code'] == 'activity_run_unavailable'
    assert disabled.status_code == 409
    assert disabled.json()['error']['code'] == 'activity_run_unavailable'
