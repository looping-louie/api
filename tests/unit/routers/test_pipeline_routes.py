"""HTTP contract tests for pipeline routes and validation errors."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.pipelines import PipelineController
from src.app.models.pipeline_run import PipelineRunDocument, PipelineRunEventDocument
from src.app.routers.pipelines import router as pipelines_router
from src.app.routers.pipeline_runs import router as pipeline_runs_router
from src.app.services.shared.tenant import TenantService
from src.app.services.pipeline_runs import PipelineRunService
from src.app.services.pipeline_runs.readiness import PipelineRunReadiness
from src.app.utils.http import register_exception_handlers
from tests.unit.services.pipelines.test_service import build_service


def build_client(
    *,
    tenant_service: TenantService,
    pipeline_run_service: PipelineRunService | None = None,
) -> TestClient:
    """Build an authenticated pipeline application with in-memory storage."""

    service, _ = build_service(tenant_service=tenant_service)
    app = FastAPI()
    app.state.pipeline_controller = PipelineController(
        pipeline_service=service,
        pipeline_run_service=pipeline_run_service,
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
    app.include_router(pipeline_runs_router, prefix='/api/v1')
    return TestClient(app)


def pipeline_payload(
    *,
    name: str = 'Implementation_pipeline',
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
                activity_payload('Implementation_activity'),
                activity_payload('Validation_activity'),
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
            'agents': [
                {
                    'persona_id': 'persona-1',
                    'role': 'generator',
                }
            ],
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
        'Implementation_activity',
        'Validation_activity',
    ]

    fetched = client.get(f'/api/v1/pipelines/{pipeline_id}')
    listed_before_update = client.get('/api/v1/pipelines')
    patched = client.patch(
        f'/api/v1/pipelines/{pipeline_id}',
        json={
            'steps': [
                    activity_payload('Review_activity'),
                    activity_payload('Approval_activity'),
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
            'Review_activity',
            'Approval_activity',
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


def test_pipeline_accepts_one_step_and_rejects_invalid_steps(
    tenant_service: TenantService,
) -> None:
    """One valid step is sufficient, while empty and malformed arrays fail."""

    client = build_client(tenant_service=tenant_service)
    single_step_response = client.post(
        '/api/v1/pipelines',
        json=pipeline_payload(steps=[activity_payload('Only_activity')]),
    )
    invalid_steps = (
        [],
        [{}, activity_payload('Valid activity')],
    )

    assert single_step_response.status_code == 201
    assert [step['name'] for step in single_step_response.json()['steps']] == [
            'Only_activity',
    ]

    for steps in invalid_steps:
        response = client.post(
            '/api/v1/pipelines',
            json=pipeline_payload(steps=steps),
        )
        assert response.status_code == 422
        assert response.json()['error']['code'] == 'invalid_pipeline_steps'


def test_pipeline_rejects_invalid_pipeline_and_activity_names(
    tenant_service: TenantService,
) -> None:
    """Pipeline and inline Activity names share the resource-name contract."""

    client = build_client(tenant_service=tenant_service)
    invalid_pipeline = client.post(
        '/api/v1/pipelines',
        json=pipeline_payload(name='Invalid pipeline'),
    )
    invalid_activity = client.post(
        '/api/v1/pipelines',
        json=pipeline_payload(steps=[activity_payload('Invalid activity')]),
    )

    assert invalid_pipeline.status_code == 422
    assert invalid_pipeline.json()['error']['code'] == 'request_validation_error'
    assert invalid_activity.status_code == 422
    assert invalid_activity.json()['error']['code'] == 'invalid_pipeline_steps'


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


def test_pipeline_persists_nullable_and_supported_harness_overrides(
    tenant_service: TenantService,
) -> None:
    """Pipelines inherit an unset Harness and accept an empty Codex override."""

    client = build_client(tenant_service=tenant_service)
    created = client.post('/api/v1/pipelines', json=pipeline_payload())
    codex = client.post(
        '/api/v1/pipelines',
        json={
            **pipeline_payload(),
            'harness': {'kind': 'codex_cli', 'version': 'v1', 'config': {}},
        },
    )
    invalid_config = client.post(
        '/api/v1/pipelines',
        json={
            **pipeline_payload(),
            'harness': {
                'kind': 'louie',
                'version': 'v1',
                'config': {'sandbox': 'workspace-write'},
            },
        },
    )

    assert created.status_code == 201
    assert created.json()['harness'] is None
    assert codex.status_code == 201
    assert codex.json()['harness'] == {
        'kind': 'codex_cli',
        'version': 'v1',
        'config': {},
    }
    assert invalid_config.status_code == 422


def test_pipeline_returns_an_explicit_logical_model_id(
    tenant_service: TenantService,
) -> None:
    """A persisted Pipeline model ID serializes in its HTTP response."""

    client = build_client(tenant_service=tenant_service)

    response = client.post(
        '/api/v1/pipelines',
        json={
            **pipeline_payload(),
            'model_id': 'gpt-5',
        },
    )

    assert response.status_code == 201
    assert response.json()['model_id'] == 'gpt-5'


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


def test_pipeline_lease_renewal_requires_a_token(
    tenant_service: TenantService,
) -> None:
    """The runtime lease route validates the token and returns its new expiry."""

    client = build_client(
        tenant_service=tenant_service,
        pipeline_run_service=cast(PipelineRunService, _LeaseService()),
    )

    response = client.post(
        '/api/v1/pipelines/pipeline-1/runs/run-1/lease',
        json={'lease_token': 'lease-1'},
    )
    invalid = client.post(
        '/api/v1/pipelines/pipeline-1/runs/run-1/lease',
        json={},
    )

    assert response.status_code == 200
    assert response.json() == {'lease_expires_at': '2026-08-19T10:01:00Z'}
    assert invalid.status_code == 422
    assert invalid.json()['error']['code'] == 'request_validation_error'


def test_pipeline_claimable_filter_accepts_standard_boolean_query(
    tenant_service: TenantService,
) -> None:
    """Claimable-run listing accepts the runtime's standard boolean encoding."""

    service = _ClaimableService()
    client = build_client(
        tenant_service=tenant_service,
        pipeline_run_service=cast(PipelineRunService, service),
    )

    response = client.get('/api/v1/pipelines/pipeline-1/runs?claimable=true')
    missing_filter = client.get('/api/v1/pipelines/pipeline-1/runs')
    false_filter = client.get('/api/v1/pipelines/pipeline-1/runs?claimable=false')

    assert response.status_code == 200
    assert response.json() == {'items': [], 'total': 0}
    assert service.was_called
    assert missing_filter.status_code == 422
    assert missing_filter.json()['error']['code'] == 'request_validation_error'
    assert false_filter.status_code == 422


def test_pipeline_run_catalog_forwards_project_filters(
    tenant_service: TenantService,
) -> None:
    """Run discovery accepts the web catalog's Project-scoped filters."""

    service = _RunListService()
    client = build_client(
        tenant_service=tenant_service,
        pipeline_run_service=cast(PipelineRunService, service),
    )

    response = client.get(
        '/api/v1/pipeline-runs',
        params={
            'offset': 10,
            'pipeline_id': 'pipeline-1',
            'status': 'completed',
            'created_from': '2026-08-20T00:00:00Z',
            'created_to': '2026-08-22T00:00:00Z',
        },
        headers={'X-Project-ID': 'workspace-1'},
    )

    assert response.status_code == 200
    assert response.json() == {'items': [], 'total': 0}
    assert service.filters == (
        'user-1', 10, 'pipeline-1', 'completed',
        datetime(2026, 8, 20, tzinfo=UTC),
        datetime(2026, 8, 22, tzinfo=UTC),
        'workspace-1',
    )


def test_pipeline_event_ledger_returns_persisted_events(
    tenant_service: TenantService,
) -> None:
    """Pipeline event listing serializes immutable persisted run events."""

    client = build_client(
        tenant_service=tenant_service,
        pipeline_run_service=cast(PipelineRunService, _EventService()),
    )

    response = client.get('/api/v1/pipelines/pipeline-1/runs/run-1/events')

    assert response.status_code == 200
    assert response.json() == {
        'items': [{
            'id': 'event-1',
            'event_type': 'pipeline_run_created',
            'activity_id': None,
            'actor_id': 'user-1',
            'payload': {'commit_mode': 'forbid'},
            'created_at': '2026-08-21T00:00:00Z',
        }],
        'total': 1,
    }


def test_pipeline_run_readiness_returns_aggregated_worker_state(
    tenant_service: TenantService,
) -> None:
    """Queued-run readiness exposes Harness and workspace worker counts."""

    client = build_client(
        tenant_service=tenant_service,
        pipeline_run_service=cast(PipelineRunService, _ReadinessService()),
    )

    response = client.get(
        '/api/v1/pipelines/pipeline-1/runs/run-1/readiness',
    )

    assert response.status_code == 200
    assert response.json() == {
        'status': 'no_compatible_workers',
        'project_id': 'workspace-1',
        'required_harness': {
            'kind': 'codex_cli', 'version': 'v1', 'config': {},
        },
        'registered_worker_count': 2,
        'active_worker_count': 1,
        'compatible_worker_count': 0,
        'latest_heartbeat_at': '2026-08-21T00:00:00Z',
        'observed_at': '2026-08-21T00:00:30Z',
    }


def test_pipeline_claim_requires_an_if_match_header(
    tenant_service: TenantService,
) -> None:
    """Conditional claims reject requests that omit the listed candidate ETag."""

    client = build_client(
        tenant_service=tenant_service,
        pipeline_run_service=cast(PipelineRunService, _LeaseService()),
    )

    response = client.patch(
        '/api/v1/pipelines/pipeline-1/runs/run-1',
        json={'worker_id': 'worker-1', 'status': 'claimed'},
    )

    assert response.status_code == 422
    assert response.json()['error']['code'] == 'request_validation_error'


def test_pipeline_start_requires_no_worker_or_checkout_payload(
    tenant_service: TenantService,
) -> None:
    """Starting delegates admission of a prepared run to the scheduler."""

    client = build_client(
        tenant_service=tenant_service,
        pipeline_run_service=cast(PipelineRunService, _StartService()),
    )

    response = client.post('/api/v1/pipelines/pipeline-1/runs/run-1/start')

    assert response.status_code == 200
    assert response.json()['status'] == 'queued'
    assert response.json()['current_activity_run'] is None


def test_pipeline_run_creation_exposes_disabled_model_details(
    tenant_service: TenantService,
) -> None:
    """Run preparation failures identify the model the User must enable."""

    client = build_client(
        tenant_service=tenant_service,
        pipeline_run_service=cast(
            PipelineRunService,
            _UnavailableCreateService(),
        ),
    )

    response = client.post(
        '/api/v1/pipelines/pipeline-1/runs',
        json={'input': 'Implement.'},
    )

    assert response.status_code == 409
    assert response.json()['error']['code'] == 'pipeline_run_unavailable'
    assert response.json()['error']['details'] == {
        'resource_type': 'pipeline',
        'resource_id': 'pipeline-1',
        'reason': 'model_disabled',
        'activity_id': 'activity-1',
        'model_id': 'model-disabled',
    }


class _LeaseService:
    """Provide a deterministic renewal response for the router contract test."""

    async def renew_lease(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        run_id: str,
        lease_token: str,
        lease_duration: timedelta,
        requested_project_id: str | None,
    ) -> object:
        """Return a run-shaped object containing the renewed lease expiry."""

        assert (user_id, pipeline_id, run_id, lease_token) == (
            'user-1', 'pipeline-1', 'run-1', 'lease-1',
        )
        assert lease_duration == timedelta(minutes=1)
        assert requested_project_id is None
        return type(
            'RenewedRun',
            (),
            {'lease_expires_at': datetime(2026, 8, 19, 10, 1, tzinfo=UTC)},
        )()


class _ClaimableService:
    """Provide an empty candidate list for claimable-route testing."""

    def __init__(self) -> None:
        """Initialize the invocation marker."""

        self.was_called = False

    async def list_claimable(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        requested_project_id: str | None,
    ) -> list[PipelineRunDocument]:
        """Record the claimable-list request and return no candidates."""

        assert (user_id, pipeline_id, requested_project_id) == (
            'user-1', 'pipeline-1', None,
        )
        self.was_called = True
        return []


class _RunListService:
    """Record filters supplied to the Project run catalog."""

    def __init__(self) -> None:
        """Initialize the observed filter tuple."""

        self.filters: tuple[object, ...] | None = None

    async def list(self, **filters: object) -> tuple[list[PipelineRunDocument], int]:
        """Record normalized controller arguments and return an empty page."""

        self.filters = (
            filters['user_id'], filters['offset'], filters['pipeline_id'],
            filters['status'], filters['created_from'], filters['created_to'],
            filters['requested_project_id'],
        )
        return [], 0


class _EventService:
    """Provide one persisted event for event-ledger route testing."""

    async def get(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        run_id: str,
        requested_project_id: str | None,
    ) -> tuple[PipelineRunDocument, None]:
        """Return one completed Pipeline run with its immutable event ledger."""

        assert (user_id, pipeline_id, run_id, requested_project_id) == (
            'user-1', 'pipeline-1', 'run-1', None,
        )
        timestamp = datetime(2026, 8, 21, tzinfo=UTC)
        return PipelineRunDocument(
            id='run-1', project_id='workspace-1', pipeline_id='pipeline-1',
            input='Implement.', commit_mode='forbid', status='completed',
            worker_id=None, lease_token=None, lease_expires_at=None, attempt=0,
            current_activity_run_id=None, pipeline_snapshot={'steps': []}, steps=(),
            created_at=timestamp, created_by='user-1', updated_at=timestamp,
            events=(PipelineRunEventDocument(
                id='event-1', project_id='workspace-1', pipeline_run_id='run-1',
                event_type='pipeline_run_created', activity_id=None, actor_id='user-1',
                payload={'commit_mode': 'forbid'}, created_at=timestamp,
            ),),
        ), None


class _ReadinessService:
    """Provide one deterministic queued-run worker diagnostic."""

    async def readiness(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        run_id: str,
        requested_project_id: str | None,
    ) -> PipelineRunReadiness:
        """Return an active Worker set without the required Codex Harness."""

        assert (user_id, pipeline_id, run_id, requested_project_id) == (
            'user-1', 'pipeline-1', 'run-1', None,
        )
        return PipelineRunReadiness(
            status='no_compatible_workers', project_id='workspace-1',
            required_harness={
                'kind': 'codex_cli', 'version': 'v1', 'config': {},
            },
            registered_worker_count=2, active_worker_count=1,
            compatible_worker_count=0,
            latest_heartbeat_at=datetime(2026, 8, 21, tzinfo=UTC),
            observed_at=datetime(2026, 8, 21, 0, 0, 30, tzinfo=UTC),
        )


class _StartService:
    """Provide a deterministic prepared-run start response for route tests."""

    async def start(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        run_id: str,
        requested_project_id: str | None,
    ) -> tuple[PipelineRunDocument, None]:
        """Return a runtime-queued PipelineRun without a local execution payload."""

        assert (user_id, pipeline_id, run_id, requested_project_id) == (
            'user-1', 'pipeline-1', 'run-1', None,
        )
        timestamp = datetime(2026, 8, 19, tzinfo=UTC)
        return PipelineRunDocument(
            id='run-1', project_id='workspace-1', pipeline_id='pipeline-1',
            input='Implement.', commit_mode='allow', status='queued',
            worker_id=None, lease_token=None, lease_expires_at=None, attempt=0,
            current_activity_run_id=None, pipeline_snapshot={'steps': []},
            steps=(), created_at=timestamp, created_by='user-1', updated_at=timestamp,
        ), None


class _UnavailableCreateService:
    """Reject run creation with one actionable model-policy failure."""

    async def create(self, **_: object) -> tuple[PipelineRunDocument, None]:
        """Raise the same domain error produced before run persistence."""

        from src.app.services.pipeline_runs import PipelineRunUnavailableError

        raise PipelineRunUnavailableError(
            pipeline_id='pipeline-1',
            reason="model 'model-disabled' is disabled",
            reason_code='model_disabled',
            activity_id='activity-1',
            model_id='model-disabled',
        )


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


def test_pipeline_rejects_invalid_direct_loop_roles(
    tenant_service: TenantService,
) -> None:
    """Inline direct-loop steps must have one generator and no other roles."""

    client = build_client(tenant_service=tenant_service)
    invalid_agents = (
        [],
        [
            {'persona_id': 'persona-1', 'role': 'generator'},
            {'persona_id': 'persona-2', 'role': 'reviewer'},
        ],
    )
    for agents in invalid_agents:
        response = client.post(
            '/api/v1/pipelines',
            json=pipeline_payload(
                steps=[
                    {
                        **activity_payload('Implementation activity'),
                        'config': {
                            **activity_payload('Implementation activity')['config'],
                            'agents': agents,
                        },
                    },
                    activity_payload('Validation activity'),
                ],
            ),
        )

        assert response.status_code == 422
        assert response.json()['error']['code'] == 'invalid_pipeline_steps'
