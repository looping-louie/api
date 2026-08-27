"""HTTP contract tests for workspace worker registration routes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.worker import WorkerController
from src.app.models.worker import WorkerDocument
from src.app.routers.workers import router
from src.app.services.shared.tenant import TenantService
from src.app.services.workers import WorkerService
from src.app.utils.http import register_exception_handlers
from tests.conftest import IncrementingClock


class InMemoryWorkerRepository:
    """Persist workspace workers for HTTP route tests."""

    def __init__(self) -> None:
        """Initialize worker storage keyed by workspace and identifier."""

        self.documents: dict[tuple[str, str], WorkerDocument] = {}

    async def create(self, document: WorkerDocument) -> WorkerDocument:
        """Persist a newly provisioned worker."""

        self.documents[(document.project_id, document.id)] = document
        return document

    async def heartbeat(
        self,
        *,
        project_id: str,
        worker_id: str,
        occurred_at: datetime,
    ) -> WorkerDocument | None:
        """Update the stored worker heartbeat when it exists."""

        current = self.documents.get((project_id, worker_id))
        if current is None:
            return None
        updated = WorkerDocument(
            id=current.id,
            project_id=current.project_id,
            registered_at=current.registered_at,
            last_heartbeat_at=occurred_at,
            harnesses=current.harnesses,
        )
        self.documents[(project_id, worker_id)] = updated
        return updated

    async def get(
        self,
        *,
        project_id: str,
        worker_id: str,
    ) -> WorkerDocument | None:
        """Return one stored Worker capability registration."""

        return self.documents.get((project_id, worker_id))

    async def is_active(
        self,
        *,
        project_id: str,
        worker_id: str,
        active_since: datetime,
    ) -> bool:
        """Return whether a worker has sent a current heartbeat."""

        worker = self.documents.get((project_id, worker_id))
        return worker is not None and worker.last_heartbeat_at >= active_since


def build_client(tenant_service: TenantService) -> TestClient:
    """Build an authenticated worker registration API application."""

    app = FastAPI()
    app.state.worker_controller = WorkerController(
        worker_service=WorkerService(
            repository=InMemoryWorkerRepository(),
            tenant_service=tenant_service,
            id_factory=lambda: 'worker-1',
            clock=IncrementingClock(),
        ),
    )

    @app.middleware('http')
    async def add_authenticated_user(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Inject the actor required by workspace route dependencies."""

        request.state.user_id = 'user-1'
        return await call_next(request)

    register_exception_handlers(app)
    app.include_router(router, prefix='/api/v1')
    return TestClient(app)


def test_create_then_heartbeat_refreshes_one_workspace_worker(
    tenant_service: TenantService,
) -> None:
    """API provisioning and heartbeat expose worker lifecycle timestamps."""

    client = build_client(tenant_service)
    headers = {'X-Project-ID': 'workspace-1'}

    registered = client.post('/api/v1/workers', headers=headers)
    heartbeated = client.post(
        '/api/v1/workers/worker-1/heartbeat',
        headers=headers,
    )

    assert registered.status_code == 201
    assert heartbeated.status_code == 200
    assert registered.json()['id'] == 'worker-1'
    assert registered.json()['harnesses'] == [{
        'kind': 'louie',
        'version': 'v1',
        'config': {},
    }]
    assert heartbeated.json()['harnesses'] == registered.json()['harnesses']
    assert heartbeated.json()['registered_at'] == registered.json()['registered_at']
    assert heartbeated.json()['last_heartbeat_at'] > registered.json()['last_heartbeat_at']


def test_worker_registration_accepts_codex_cli_harness(
    tenant_service: TenantService,
) -> None:
    """Registration persists the initial Codex CLI Harness capability."""

    response = build_client(tenant_service).post(
        '/api/v1/workers',
        headers={'X-Project-ID': 'workspace-1'},
        json={
            'harnesses': [
                {'kind': 'codex_cli', 'version': 'v1', 'config': {}},
            ],
        },
    )

    assert response.status_code == 201
    assert response.json()['harnesses'] == [{
        'kind': 'codex_cli',
        'version': 'v1',
        'config': {},
    }]


def test_heartbeat_requires_workspace_worker_registration(
    tenant_service: TenantService,
) -> None:
    """A heartbeat cannot implicitly create an unregistered worker."""

    response = build_client(tenant_service).post('/api/v1/workers/worker-1/heartbeat')

    assert response.status_code == 404
    assert response.json()['error']['code'] == 'worker_not_found'
