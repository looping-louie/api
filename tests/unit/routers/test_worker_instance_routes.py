"""HTTP contract tests for Worker lifecycle routes."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.controllers.worker_instances import WorkerInstanceController
from datetime import datetime

from src.app.models.worker import WorkerHarnessCapability
from src.app.models.worker_instance import (
    WorkerInstanceDocument,
    WorkerInstanceProjectDocument,
    WorkerProjectEnablementDocument,
)
from src.app.routers.workers import router
from src.app.services.shared.tenant import TenantService
from src.app.services.worker_instances import WorkerInstanceService
from src.app.utils.http import register_exception_handlers
from tests.conftest import IncrementingClock


class InMemoryWorkerInstanceRepository:
    """Persist Workers for HTTP route tests."""

    def __init__(self) -> None:
        """Initialize Worker and Project enablement storage."""

        self.workers: dict[str, WorkerInstanceDocument] = {}
        self.enablements: list[WorkerProjectEnablementDocument] = []

    async def get(
        self,
        *,
        worker_instance_id: str,
    ) -> WorkerInstanceDocument | None:
        """Return one stored Worker."""

        return self.workers.get(worker_instance_id)

    async def get_for_owner(
        self,
        *,
        worker_instance_id: str,
        owner_user_id: str,
    ) -> WorkerInstanceDocument | None:
        """Return one Worker owned by the specified User."""

        worker = self.workers.get(worker_instance_id)
        if worker is None or worker.owner_user_id != owner_user_id:
            return None
        return worker

    async def create(
        self,
        document: WorkerInstanceDocument,
    ) -> WorkerInstanceDocument:
        """Store one Worker."""

        self.workers[document.id] = document
        return document

    async def heartbeat(
        self,
        *,
        worker_instance_id: str,
        occurred_at: datetime,
        harnesses: tuple[WorkerHarnessCapability, ...],
    ) -> WorkerInstanceDocument | None:
        """Update one Worker's liveness and Harnesses."""

        current = self.workers.get(worker_instance_id)
        if current is None:
            return None
        updated = WorkerInstanceDocument(
            id=current.id,
            owner_user_id=current.owner_user_id,
            registered_at=current.registered_at,
            last_heartbeat_at=occurred_at,
            harnesses=harnesses,
        )
        self.workers[updated.id] = updated
        return updated

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

    async def list_enabled(
        self,
        *,
        project_id: str,
    ) -> tuple[WorkerInstanceProjectDocument, ...]:
        """Return Workers enabled for one Project."""

        return tuple(
            WorkerInstanceProjectDocument(
                worker=self.workers[enablement.worker_instance_id],
                enablement=enablement,
            )
            for enablement in self.enablements
            if enablement.project_id == project_id
        )


class InMemoryPipelineRunRepository:
    """Provide active Worker lease counts for HTTP route tests."""

    async def active_claim_counts(
        self,
        *,
        worker_ids: tuple[str, ...],
        observed_at: datetime,
    ) -> dict[str, int]:
        """Return no active leases for the test Workers."""

        del worker_ids, observed_at
        return {}


def build_client(tenant_service: TenantService) -> TestClient:
    """Build an authenticated Worker API application."""

    app = FastAPI()
    app.state.worker_instance_controller = WorkerInstanceController(
        service=WorkerInstanceService(
            repository=InMemoryWorkerInstanceRepository(),
            tenant_service=tenant_service,
            id_factory=lambda: 'worker-1',
            clock=IncrementingClock(),
        ),
        pipeline_run_repository=InMemoryPipelineRunRepository(),
        clock=IncrementingClock(),
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
        '/api/v1/workers',
        json={
            'project_id': 'workspace-1',
            'harnesses': [{'kind': 'codex_cli'}],
        },
    )
    enabled = client.post(
        '/api/v1/workers/worker-1/projects/workspace-1',
    )
    heartbeated = client.post(
        '/api/v1/workers/worker-1/heartbeat',
        json={'harnesses': []},
    )

    assert registered.status_code == 201
    assert registered.json()['id'] == 'worker-1'
    assert enabled.status_code == 201
    assert enabled.json()['worker_id'] == 'worker-1'
    assert enabled.json()['project_id'] == 'workspace-1'
    assert heartbeated.status_code == 200
    assert heartbeated.json()['harnesses'] == []


def test_global_worker_registration_requires_an_explicit_project(
    tenant_service: TenantService,
) -> None:
    """A Worker cannot receive an implicit initial Project assignment."""

    response = build_client(tenant_service).post(
        '/api/v1/workers',
        json={'harnesses': []},
    )

    assert response.status_code == 422


def test_lists_global_workers_enabled_for_selected_project(
    tenant_service: TenantService,
) -> None:
    """A Project sees only its enabled Worker operational state."""

    client = build_client(tenant_service)
    client.post(
        '/api/v1/workers',
        json={
            'project_id': 'workspace-1',
            'harnesses': [{'kind': 'codex_cli'}],
        },
    )

    response = client.get(
        '/api/v1/workers?project_id=workspace-1',
    )

    assert response.status_code == 200
    assert response.json() == [{
        'id': 'worker-1',
        'registered_at': '2026-07-13T10:00:00Z',
        'last_heartbeat_at': '2026-07-13T10:00:00Z',
        'harnesses': [{'kind': 'codex_cli', 'version': 'v1', 'config': {}}],
        'enabled_at': '2026-07-13T10:00:00Z',
        'active': True,
        'active_claims': 0,
        'capacity': 1,
    }]


def test_listing_global_workers_requires_a_project_filter(
    tenant_service: TenantService,
) -> None:
    """Worker collection reads require an explicit Project query filter."""

    response = build_client(tenant_service).get('/api/v1/workers')

    assert response.status_code == 422


def test_describes_worker_owned_by_requesting_user(
    tenant_service: TenantService,
) -> None:
    """A Worker detail read omits Project enablement state."""

    client = build_client(tenant_service)
    client.post(
        '/api/v1/workers',
        json={
            'project_id': 'workspace-1',
            'harnesses': [{'kind': 'codex_cli'}],
        },
    )

    response = client.get('/api/v1/workers/worker-1')

    assert response.status_code == 200
    assert response.json() == {
        'id': 'worker-1',
        'registered_at': '2026-07-13T10:00:00Z',
        'last_heartbeat_at': '2026-07-13T10:00:00Z',
        'harnesses': [{'kind': 'codex_cli', 'version': 'v1', 'config': {}}],
    }


def test_does_not_describe_missing_worker(
    tenant_service: TenantService,
) -> None:
    """A missing Worker detail read returns the stable not-found error."""

    response = build_client(tenant_service).get('/api/v1/workers/worker-missing')

    assert response.status_code == 404
    assert response.json()['error']['code'] == 'worker_not_found'
