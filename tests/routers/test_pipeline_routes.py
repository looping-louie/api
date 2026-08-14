"""HTTP contract tests for pipeline routes and validation errors."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.pipeline import PipelineController
from src.app.routers.pipelines import router as pipelines_router
from src.app.services.shared.tenant import TenantService
from src.app.utils.http import register_exception_handlers
from tests.services.pipelines.test_service import build_service


def build_client(*, tenant_service: TenantService) -> TestClient:
    """Build an authenticated pipeline application with in-memory storage."""

    service, _ = build_service(tenant_service=tenant_service)
    app = FastAPI()
    app.state.pipeline_controller = PipelineController(
        pipeline_service=service,
    )

    @app.middleware('http')
    async def add_authenticated_user(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Inject the actor required by route dependencies."""

        request.state.user_id = 'user-1'
        return await call_next(request)

    register_exception_handlers(app)
    app.include_router(pipelines_router, prefix='/api/v1')
    return TestClient(app)


def pipeline_payload(
    *,
    name: str = 'Implementation pipeline',
    steps: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Build one valid pipeline creation body."""

    return {
        'name': name,
        'description': 'Implement and validate.',
        'steps': (
            steps
            if steps is not None
            else [
                activity_payload('Implementation activity'),
                activity_payload('Validation activity'),
            ]
        ),
    }


def activity_payload(
    name: str,
    depends_on: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Build one valid inline Activity definition."""

    payload: dict[str, object] = {
        'name': name,
        'description': 'Complete one pipeline stage.',
        'type': 'direct_loop',
        'config': {
            'stop_conditions': {'max_iterations': 1},
            'agents': [],
            'output_contract': {
                'type': 'text',
                'description': 'A pipeline stage result.',
            },
        },
    }
    if depends_on is not None:
        payload['dependsOn'] = depends_on
    return payload


def test_pipeline_crud_changelog_and_archival_routes(
    tenant_service: TenantService,
) -> None:
    """Create, read, replace, audit, and archive use REST contracts."""

    client = build_client(tenant_service=tenant_service)
    created_response = client.post('/api/v1/pipelines', json=pipeline_payload())
    assert created_response.status_code == 201
    created = created_response.json()
    pipeline_id = created['id']
    assert len(created['steps']) == 2
    assert all(step['id'] for step in created['steps'])
    assert [step['name'] for step in created['steps']] == [
        'Implementation activity',
        'Validation activity',
    ]

    fetched = client.get(f'/api/v1/pipelines/{pipeline_id}')
    listed_before_update = client.get('/api/v1/pipelines')
    patched = client.patch(
        f'/api/v1/pipelines/{pipeline_id}',
        json={
            'steps': [
                activity_payload('Review activity'),
                activity_payload('Approval activity'),
            ]
        },
    )
    changelog = client.get(f'/api/v1/pipelines/{pipeline_id}/changelog')
    deleted = client.delete(f'/api/v1/pipelines/{pipeline_id}')
    listed = client.get('/api/v1/pipelines')
    archived = client.get('/api/v1/pipelines?status=archived')

    assert fetched.status_code == 200
    assert fetched.json()['steps'] == created['steps']
    assert listed_before_update.json()['items'][0]['steps'] == created['steps']
    assert [step['name'] for step in patched.json()['steps']] == [
        'Review activity',
        'Approval activity',
    ]
    assert all(step['id'] for step in patched.json()['steps'])
    assert patched.json()['steps'][0]['id'] != created['steps'][0]['id']
    assert changelog.json()['items'][0]['diff']['steps']['changed']
    assert not changelog.json()['items'][0]['diff']['steps']['order_changes']
    assert deleted.json() == {'deleted': True}
    assert listed.json() == {'items': [], 'total': 0}
    assert archived.json()['total'] == 1
    conflict = client.patch(
        f'/api/v1/pipelines/{pipeline_id}',
        json={'enabled': True},
    )
    assert conflict.status_code == 409
    assert conflict.json()['error']['code'] == 'pipeline_archived'


def test_invalid_pipeline_steps_use_stable_error_envelope(
    tenant_service: TenantService,
) -> None:
    """Missing activity IDs and short arrays use validation envelopes."""

    client = build_client(tenant_service=tenant_service)
    invalid_steps = (
        [],
        [activity_payload('Only activity')],
        [{}, activity_payload('Valid activity')],
    )
    for steps in invalid_steps:
        response = client.post(
            '/api/v1/pipelines',
            json=pipeline_payload(steps=steps),
        )
        assert response.status_code == 422
        assert response.json()['error']['code'] == 'invalid_pipeline_steps'


def test_pipeline_creation_persists_inline_activity_definitions(
    tenant_service: TenantService,
) -> None:
    """Pipeline creation accepts definitions without pre-existing Activity IDs."""

    client = build_client(tenant_service=tenant_service)
    response = client.post(
        '/api/v1/pipelines',
        json=pipeline_payload(),
    )

    assert response.status_code == 201
    assert len(response.json()['steps']) == 2


def test_pipeline_returns_named_step_dependencies(
    tenant_service: TenantService,
) -> None:
    """Pipeline responses expose graph edges with named Activity conditions."""

    client = build_client(tenant_service=tenant_service)
    response = client.post(
        '/api/v1/pipelines',
        json=pipeline_payload(
            steps=[
                activity_payload('Prepare'),
                activity_payload(
                    'Validate',
                    [{'activity': 'Prepare', 'condition': 'success'}],
                ),
            ],
        ),
    )

    assert response.status_code == 201
    assert response.json()['steps'][0]['dependsOn'] == []
    assert response.json()['steps'][1]['dependsOn'] == [
        {'activity': 'Prepare', 'condition': 'success'},
    ]


def test_pipeline_rejects_retired_dependency_condition(
    tenant_service: TenantService,
) -> None:
    """Pipeline dependency conditions must use success, not the retired succeed value."""

    client = build_client(tenant_service=tenant_service)
    response = client.post(
        '/api/v1/pipelines',
        json=pipeline_payload(
            steps=[
                activity_payload('Prepare'),
                activity_payload(
                    'Validate',
                    [{'activity': 'Prepare', 'condition': 'succeed'}],
                ),
            ],
        ),
    )

    assert response.status_code == 422
    assert response.json()['error']['code'] == 'invalid_pipeline_steps'


def test_generic_body_validation_also_uses_api_envelope(
    tenant_service: TenantService,
) -> None:
    """Non-step request failures no longer return FastAPI's detail shape."""

    client = build_client(tenant_service=tenant_service)
    response = client.post(
        '/api/v1/pipelines',
        json={'description': 'Missing name.', 'steps': []},
    )

    assert response.status_code == 422
    assert 'error' in response.json() and 'detail' not in response.json()


def test_pipeline_rejects_legacy_title_field(
    tenant_service: TenantService,
) -> None:
    """Pipeline requests require the public name field."""

    client = build_client(tenant_service=tenant_service)
    response = client.post(
        '/api/v1/pipelines',
        json={
            'title': 'Legacy title',
            'description': 'Reject the retired field.',
            'steps': [activity_payload('First'), activity_payload('Second')],
        },
    )

    assert response.status_code == 422
    assert response.json()['error']['code'] == 'request_validation_error'
