"""HTTP contract tests for global Worker lifecycle routes."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.worker_instances import WorkerInstanceController
from src.app.models.worker_instance import (
    WorkerInstanceDocument,
    WorkerProjectEnablementDocument,
)
from src.app.routers.workers import router
from src.app.services.shared.tenant import TenantService
from src.app.services.worker_instances import WorkerInstanceService
from src.app.utils.http import register_exception_handlers
from tests.conftest import IncrementingClock


class InMemoryWorkerInstanceRepository:
    """Persist global Workers for HTTP route tests."""

    def __init__(self) -> None:
        """Initialize Worker and Project enablement storage."""

        self.workers: dict[str, WorkerInstanceDocument] = {}
        self.enablements: list[WorkerProjectEnablementDocument] = []

    async def get(
        self,
        *,
        worker_instance_id: str,
    ) -> WorkerInstanceDocument | None:
        """Return one stored global Worker."""

        return self.workers.get(worker_instance_id)

    async def create(
        self,
        document: WorkerInstanceDocument,
    ) -> WorkerInstanceDocument:
        """Store one global Worker."""

        self.workers[document.id] = document
        return document

    async def enable_project(
        self,
        document: WorkerProjectEnablementDocument,
    ) -> WorkerProjectEnablementDocument:
        """Store one Worker Project enablement."""

        self.enablements.append(document)
        return document

    async def list_enabled_projects(
        self,
        *,
        worker_instance_id: str,
    ) -> tuple[WorkerProjectEnablementDocument, ...]:
        """Return enablements associated with one Worker."""

        return tuple(
            enablement
            for enablement in self.enablements
            if enablement.worker_instance_id == worker_instance_id
        )


def build_client(tenant_service: TenantService) -> TestClient:
    """Build an authenticated global Worker API application."""

    app = FastAPI()
    app.state.worker_instance_controller = WorkerInstanceController(
        service=WorkerInstanceService(
            repository=InMemoryWorkerInstanceRepository(),
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
        """Inject the actor required by Worker route dependencies."""

        request.state.user_id = 'user-1'
        return await call_next(request)

    register_exception_handlers(app)
    app.include_router(router, prefix='/api/v1')
    return TestClient(app)


def test_register_then_enable_global_worker_for_another_project(
    tenant_service: TenantService,
) -> None:
    """A Worker has one identity and separate Project enablements."""

    client = build_client(tenant_service)
    registered = client.post(
        '/api/v1/workers/instances',
        json={
            'project_id': 'workspace-1',
            'harnesses': [{'kind': 'codex_cli'}],
        },
    )
    enabled = client.post(
        '/api/v1/workers/instances/worker-1/projects/workspace-1',
    )

    assert registered.status_code == 201
    assert registered.json()['id'] == 'worker-1'
    assert enabled.status_code == 201
    assert enabled.json()['worker_id'] == 'worker-1'
    assert enabled.json()['project_id'] == 'workspace-1'


def test_global_worker_registration_requires_an_explicit_project(
    tenant_service: TenantService,
) -> None:
    """A global Worker cannot receive an implicit initial Project assignment."""

    response = build_client(tenant_service).post(
        '/api/v1/workers/instances',
        json={'harnesses': []},
    )

    assert response.status_code == 422