"""HTTP contract tests for linked-service routes."""

from collections.abc import Awaitable, Callable
from copy import deepcopy

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from src.app.catalogs.providers import PROVIDER_CATALOG
from src.app.controllers.linked_services import LinkedServiceController
from src.app.models.linked_service import LinkedService
from src.app.routers.linked_services import router
from src.app.services.linked_services import LinkedServiceService
from src.app.services.providers.connection import ProviderConnectionError
from src.app.services.shared.tenant import TenantService
from src.app.services.shared.dependency_checker import (
    DependencyChecker,
    DependencyUsage,
)
from src.app.services.shared.reference_resolver import ResourceReference
from tests.conftest import IncrementingClock
from tests.fakes.provider_connection_service import FakeProviderConnectionService
from tests.fakes.secret_service import FakeSecretService
from src.app.utils.http import register_exception_handlers


class InMemoryLinkedServiceRepository:
    """Minimal linked-service repository for HTTP contract tests."""

    def __init__(self) -> None:
        """Initialize the in-memory service store."""
        self._services: dict[tuple[str, str], LinkedService] = {}

    async def list_for_workspace(self, workspace_id: str) -> list[LinkedService]:
        """Return copies of services owned by a workspace."""
        return [
            deepcopy(linked_service)
            for linked_service in self._services.values()
            if linked_service.workspace_id == workspace_id
        ]

    async def get(self, workspace_id: str, service_id: str) -> LinkedService | None:
        """Return one service copy when owned by the workspace."""
        linked_service = self._services.get((workspace_id, service_id))
        return deepcopy(linked_service) if linked_service is not None else None

    async def get_by_name(
        self,
        workspace_id: str,
        name: str,
    ) -> LinkedService | None:
        """Return one service copy matching a workspace-local name."""

        for linked_service in self._services.values():
            if (
                linked_service.workspace_id == workspace_id
                and linked_service.name == name
            ):
                return deepcopy(linked_service)
        return None

    async def create(self, linked_service: LinkedService) -> LinkedService:
        """Store and return a service copy."""
        self._services[(linked_service.workspace_id, linked_service.id)] = deepcopy(linked_service)
        return deepcopy(linked_service)

    async def update(self, linked_service: LinkedService) -> LinkedService:
        """Replace and return a service copy."""
        return await self.create(linked_service)

    async def delete(self, workspace_id: str, service_id: str) -> bool:
        """Delete a service and report whether it existed."""
        return self._services.pop((workspace_id, service_id), None) is not None


class PersonaSelectionDependencyRepository:
    """Report one persona selection as a linked-service dependency."""

    async def find_usages(
        self,
        *,
        workspace_id: str,
        target: ResourceReference,
    ) -> list[DependencyUsage]:
        """Return a persona usage for the requested linked service."""

        assert workspace_id == 'workspace-1'
        assert target == ResourceReference('linked_service', 'linked-service-1')
        return [
            DependencyUsage(
                source=ResourceReference('persona', 'persona-1'),
                relation='linked_service',
            )
        ]


def build_app(controller: LinkedServiceController, authenticated: bool = True) -> FastAPI:
    """Build a minimal authenticated linked-services API application."""
    app = FastAPI()
    app.state.linked_service_controller = controller
    if authenticated:
        @app.middleware('http')
        async def add_authenticated_user(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
            """Inject the user expected by request-context dependencies."""
            request.state.user_id = 'user-1'
            return await call_next(request)
    register_exception_handlers(app)
    app.include_router(router, prefix='/api/v1')
    return app


def build_controller(tenant_service: TenantService, connection_service: FakeProviderConnectionService) -> LinkedServiceController:
    """Build a deterministic linked-service controller for tests."""
    identifier = iter(('linked-service-1', 'linked-service-2'))
    service = LinkedServiceService(
        repository=InMemoryLinkedServiceRepository(), tenant_service=tenant_service,
        secret_service=FakeSecretService(), connection_service=connection_service,
        catalog=PROVIDER_CATALOG, clock=IncrementingClock(), id_factory=lambda: next(identifier),
    )
    return LinkedServiceController(linked_service_service=service)


def test_crud_keeps_api_key_write_only_and_allows_same_provider(tenant_service: TenantService) -> None:
    """Linked services have immutable IDs and independent provider instances."""
    client = TestClient(build_app(build_controller(tenant_service, FakeProviderConnectionService())))
    first = client.post('/api/v1/linked-services', json={
        'name': 'primary_openai', 'provider_type': 'openai',
        'config': {'api_key': 'sk-test-secret'},
    })
    second = client.post('/api/v1/linked-services', json={
        'name': 'secondary_openai', 'provider_type': 'openai',
        'config': {'api_key': 'sk-other-secret'},
    })
    body = first.json()

    assert first.status_code == 201
    assert second.status_code == 201
    assert body['id'] == 'linked-service-1'
    assert body['config']['configured'] is True
    assert body['config']['key_trimmed'] == 'sk-te***************'
    assert body['config']['available_models']
    assert 'sk-test-secret' not in first.text
    listed = client.get('/api/v1/linked-services')
    assert [item['name'] for item in listed.json()] == ['primary_openai', 'secondary_openai']
    patched = client.patch('/api/v1/linked-services/linked-service-1', json={'name': 'renamed_openai', 'enabled': False})
    assert patched.status_code == 200
    assert patched.json()['id'] == 'linked-service-1'
    assert patched.json()['name'] == 'renamed_openai'
    assert client.delete('/api/v1/linked-services/linked-service-1').json() == {'deleted': True}
    assert client.get('/api/v1/linked-services/linked-service-1').status_code == 404


def test_duplicate_linked_service_name_returns_conflict(tenant_service: TenantService) -> None:
    """Names remain unique inside the selected workspace."""

    client = TestClient(build_app(build_controller(tenant_service, FakeProviderConnectionService())))
    payload = {
        'name': 'primary_openai',
        'provider_type': 'openai',
        'config': {'api_key': 'sk-test-secret'},
    }

    assert client.post('/api/v1/linked-services', json=payload).status_code == 201
    response = client.post('/api/v1/linked-services', json=payload)

    assert response.status_code == 409
    assert response.json()['error']['code'] == 'linked_service_name_conflict'


def test_candidate_connection_failure_does_not_create_service(tenant_service: TenantService) -> None:
    """Failed candidate configuration tests prevent persistence."""
    connection_service = FakeProviderConnectionService()
    connection_service.error = ProviderConnectionError('Connection failed.')
    client = TestClient(build_app(build_controller(tenant_service, connection_service)))

    response = client.post('/api/v1/linked-services', json={
        'name': 'failed_openai', 'provider_type': 'openai',
        'config': {'api_key': 'sk-test-secret'},
    })

    assert response.status_code == 502
    assert response.json()['error']['code'] == 'provider_connection_error'
    assert client.get('/api/v1/linked-services').json() == []


def test_linked_service_routes_require_authentication(tenant_service: TenantService) -> None:
    """Linked service routes require an authenticated request context."""
    client = TestClient(build_app(build_controller(tenant_service, FakeProviderConnectionService()), authenticated=False))

    response = client.get('/api/v1/linked-services')

    assert response.status_code == 401


def test_linked_service_delete_is_blocked_by_persona_selection(
    tenant_service: TenantService,
) -> None:
    """A Persona selecting a linked service prevents its deletion."""

    repository = InMemoryLinkedServiceRepository()
    service = LinkedServiceService(
        repository=repository,
        tenant_service=tenant_service,
        secret_service=FakeSecretService(),
        connection_service=FakeProviderConnectionService(),
        catalog=PROVIDER_CATALOG,
        dependency_checker=DependencyChecker(
            repository=PersonaSelectionDependencyRepository(),
        ),
        clock=IncrementingClock(),
        id_factory=lambda: 'linked-service-1',
    )
    controller = LinkedServiceController(linked_service_service=service)
    client = TestClient(build_app(controller))
    created = client.post('/api/v1/linked-services', json={
        'name': 'primary_openai',
        'provider_type': 'openai',
        'config': {'api_key': 'sk-test-secret'},
    })

    response = client.delete('/api/v1/linked-services/linked-service-1')

    assert created.status_code == 201
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'resource_in_use'
