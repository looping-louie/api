"""HTTP contract tests for User-owned workspace routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app.controllers.workspace import WorkspaceController
from src.app.models.user import UserDocument
from src.app.models.workspace import WorkspaceDefaults, WorkspaceDocument
from src.app.routers.workspaces import router
from src.app.services.shared.tenant import TenantService
from src.app.services.users import UserService
from src.app.services.workspaces import WorkspaceService
from src.app.utils.http import register_exception_handlers
from tests.fakes.tenant_repository import FakeTenantRepository


class InMemoryUserRepository:
    """Store registered Users for workspace route tests."""

    def __init__(self) -> None:
        """Initialize an empty User store."""

        self.documents: dict[str, UserDocument] = {}

    async def get(self, *, user_id: str) -> UserDocument | None:
        """Return one registered User."""

        return self.documents.get(user_id)

    async def create_if_absent(self, document: UserDocument) -> UserDocument:
        """Store a User only when it is new."""

        return self.documents.setdefault(document.id, document)


class InMemoryWorkspaceRepository:
    """Store workspace documents and defaults for route tests."""

    def __init__(self) -> None:
        """Initialize empty Workspace storage."""

        self.defaults_by_workspace_id: dict[str, WorkspaceDefaults] = {}
        self.workspaces_by_user_id: dict[str, list[WorkspaceDocument]] = {}

    async def create(
        self,
        *,
        workspace: WorkspaceDocument,
        owner_id: str,
    ) -> WorkspaceDocument:
        """Store one workspace for its owner."""

        self.workspaces_by_user_id.setdefault(owner_id, []).append(workspace)
        return workspace

    async def list_for_user(self, *, user_id: str) -> list[WorkspaceDocument]:
        """Return workspaces accessible to one User."""

        return list(self.workspaces_by_user_id.get(user_id, []))

    async def get(self, *, workspace_id: str) -> WorkspaceDefaults | None:
        """Return stored defaults for one Workspace."""

        return self.defaults_by_workspace_id.get(workspace_id)

    async def replace(self, *, defaults: WorkspaceDefaults) -> WorkspaceDefaults:
        """Store replacement defaults for one Workspace."""

        self.defaults_by_workspace_id[defaults.workspace_id] = defaults
        return defaults


class FakeLinkedServiceService:
    """Provide the validation collaborator required by WorkspaceService."""

    async def require_available_selection(
        self,
        *,
        workspace_id: str,
        service_id: str,
        model_id: str,
    ) -> None:
        """Accept all model selections in route tests."""


def build_client() -> TestClient:
    """Build an application for User-owned Workspace routes."""

    user_repository = InMemoryUserRepository()
    user_service = UserService(
        repository=user_repository,
        clock=lambda: datetime(2026, 8, 26, 10, 0, tzinfo=UTC),
    )
    user_repository.documents['user-1'] = UserDocument(
        id='user-1',
        created_at=datetime(2026, 8, 26, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 8, 26, 10, 0, tzinfo=UTC),
    )
    app = FastAPI()
    app.state.workspace_controller = WorkspaceController(
        service=WorkspaceService(
            repository=InMemoryWorkspaceRepository(),
            tenant_service=TenantService(repository=FakeTenantRepository()),
            linked_service_service=FakeLinkedServiceService(),  # type: ignore[arg-type]
            user_service=user_service,
            id_factory=lambda: 'workspace-1',
            clock=lambda: datetime(2026, 8, 26, 10, 0, tzinfo=UTC),
        ),
    )
    register_exception_handlers(app)
    app.include_router(router, prefix='/api/v1')
    return TestClient(app)


def test_create_then_list_returns_a_user_owned_workspace() -> None:
    """A registered User can create and list its owned Workspace."""

    client = build_client()
    headers = {'X-User-ID': 'user-1'}

    created = client.post('/api/v1/workspaces', headers=headers, json={'name': 'Acme'})
    listed = client.get('/api/v1/workspaces', headers=headers)

    assert created.status_code == 201
    assert listed.status_code == 200
    assert created.json()['id'] == 'workspace-1'
    assert listed.json() == [created.json()]


def test_create_requires_a_registered_user() -> None:
    """An unregistered identity cannot create an owned Workspace."""

    response = build_client().post(
        '/api/v1/workspaces',
        headers={'X-User-ID': 'unknown-user'},
        json={'name': 'Acme'},
    )

    assert response.status_code == 404
    assert response.json()['error']['code'] == 'user_not_found'