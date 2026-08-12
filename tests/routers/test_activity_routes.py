"""HTTP contract tests for activity routes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from itertools import count

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.activity import ActivityController
from src.app.routers.activities import router as activities_router
from src.app.services.activities.service import ActivityService
from src.app.services.shared.tenant import TenantService
from src.app.utils.http import register_exception_handlers
from tests.fakes.activity_repository import FakeActivityRepository


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

    @app.middleware('http')
    async def add_authenticated_user(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Inject the actor required by route dependencies."""

        request.state.user_id = 'user-1'
        return await call_next(request)

    register_exception_handlers(app)
    app.include_router(activities_router, prefix='/api/v1')
    return TestClient(app)


def loop_payload() -> dict[str, object]:
    """Return one valid loop activity body."""

    return {
        'title': 'Implementation activity',
        'description': 'Produce a change.',
        'type': 'loop',
        'config': {
            'type': 'loop', 'flow': 'direct',
            'stop_conditions': {'max_tokens': 100},
            'agents': [{'model_id': 'model-1', 'persona_id': 'persona-1', 'role': 'generator'}],
            'output_contract': {'type': 'text', 'description': 'A result.'},
        },
    }


def test_activity_rest_crud_changelog_and_discriminated_configs(tenant_service: TenantService) -> None:
    """Create, read, update, audit, delete, and validate both activity types."""

    client = build_client(tenant_service=tenant_service)
    created = client.post('/api/v1/activities', json=loop_payload())
    assert created.status_code == 201
    activity_id = created.json()['id']
    assert created.json()['type'] == 'loop'
    assert created.json()['config']['flow'] == 'direct'

    gate = client.post('/api/v1/activities', json={
        'title': 'Review gate', 'description': 'Approve the result.',
        'type': 'human_gate',
        'config': {'type': 'human_gate', 'gate_type': 'quiz', 'quiz': {'questions': []}},
    })
    patched = client.patch(f'/api/v1/activities/{activity_id}', json={'status': 'disabled'})
    changelog = client.get(f'/api/v1/activities/{activity_id}/changelog')
    deleted = client.delete(f'/api/v1/activities/{activity_id}')
    retained = client.get(f'/api/v1/activities/{activity_id}/changelog')
    invalid_gate = client.post('/api/v1/activities', json={
        'title': 'Invalid', 'description': '',
        'type': 'human_gate',
        'config': {'type': 'human_gate', 'gate_type': 'approval', 'quiz': {}},
    })

    assert gate.status_code == 201
    assert gate.json()['type'] == 'human_gate'
    assert gate.json()['config']['quiz'] == {'questions': []}
    assert patched.json()['status'] == 'disabled'
    assert changelog.json()['items'][0]['change_type'] == 'disabled'
    assert changelog.json()['items'][0]['diff']['status'] == 'disabled'
    assert deleted.json() == {'deleted': True}
    assert retained.status_code == 200
    assert retained.json()['items'][0]['change_type'] == 'deleted'
    assert invalid_gate.status_code == 422


def test_activity_patch_rejects_a_config_with_a_different_type(
    tenant_service: TenantService,
) -> None:
    """An activity remains its original type after creation."""

    client = build_client(tenant_service=tenant_service)
    created = client.post('/api/v1/activities', json=loop_payload())

    response = client.patch(
        f"/api/v1/activities/{created.json()['id']}",
        json={
            'config': {
                'type': 'human_gate',
                'gate_type': 'approval',
            },
        },
    )

    assert response.status_code == 422
    assert response.json()['error']['code'] == 'activity_validation_error'
    assert response.json()['error']['details']['field'] == 'config.type'
