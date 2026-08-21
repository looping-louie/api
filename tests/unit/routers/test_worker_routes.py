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

    async def register(self, document: WorkerDocument) -> WorkerDocument:
        """Insert a worker or refresh its liveness while retaining registration time."""

        current = self.documents.get((document.workspace_id, document.id))
        stored = WorkerDocument(
            id=document.id,
            workspace_id=document.workspace_id,
            registered_at=(
                current.registered_at if current is not None else document.registered_at
            ),
            last_heartbeat_at=document.last_heartbeat_at,
        )
        self.documents[(stored.workspace_id, stored.id)] = stored
        return stored

    async def heartbeat(
        self,
        *,
        workspace_id: str,
        worker_id: str,
        occurred_at: datetime,
    ) -> WorkerDocument | None:
        """Update the stored worker heartbeat when it exists."""

        current = self.documents.get((workspace_id, worker_id))
        if current is None:
            return None
        updated = WorkerDocument(
            id=current.id,
            workspace_id=current.workspace_id,
            registered_at=current.registered_at,
            last_heartbeat_at=occurred_at,
        )
        self.documents[(workspace_id, worker_id)] = updated
        return updated

    async def is_active(
        self,
        *,
        workspace_id: str,
        worker_id: str,
        active_since: datetime,
    ) -> bool:
        """Return whether a worker has sent a current heartbeat."""

        worker = self.documents.get((workspace_id, worker_id))
        return worker is not None and worker.last_heartbeat_at >= active_since


def build_client(tenant_service: TenantService) -> TestClient:
    """Build an authenticated worker registration API application."""

    app = FastAPI()
    app.state.worker_controller = WorkerController(
        worker_service=WorkerService(
            repository=InMemoryWorkerRepository(),
            tenant_service=tenant_service,
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


def test_register_then_heartbeat_refreshes_one_workspace_worker(
    tenant_service: TenantService,
) -> None:
    """Registration and heartbeat expose stable worker lifecycle timestamps."""

    client = build_client(tenant_service)
    headers = {'X-Workspace-ID': 'workspace-1'}

    registered = client.put('/api/v1/workers/worker-1', headers=headers)
    heartbeated = client.post(
        '/api/v1/workers/worker-1/heartbeat',
        headers=headers,
    )

    assert registered.status_code == 201
    assert heartbeated.status_code == 200
    assert registered.json()['id'] == 'worker-1'
    assert heartbeated.json()['registered_at'] == registered.json()['registered_at']
    assert heartbeated.json()['last_heartbeat_at'] > registered.json()['last_heartbeat_at']


def test_heartbeat_requires_workspace_worker_registration(
    tenant_service: TenantService,
) -> None:
    """A heartbeat cannot implicitly create an unregistered worker."""

    response = build_client(tenant_service).post('/api/v1/workers/worker-1/heartbeat')

    assert response.status_code == 404
    assert response.json()['error']['code'] == 'worker_not_found'
