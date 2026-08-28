"""HTTP contract tests for User-owned Project routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app.controllers.projects import ProjectController
from src.app.models.user import UserDocument
from src.app.models.project import ProjectDocument
from src.app.routers.projects import router
from src.app.services.shared.tenant import TenantService
from src.app.services.shared.tenant import ProjectMembership
from src.app.services.users import UserService
from src.app.services.projects.service import ProjectService
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


class InMemoryProjectRepository:
    """Store Project documents for route tests."""

    def __init__(self) -> None:
        """Initialize empty Project storage."""

        self.projects_by_user_id: dict[str, list[ProjectDocument]] = {}

    async def create(
        self,
        *,
        project: ProjectDocument,
        owner_id: str,
    ) -> ProjectDocument:
        """Store one Project for its owner."""

        self.projects_by_user_id.setdefault(owner_id, []).append(project)
        return project

    async def list_for_user(self, *, user_id: str) -> list[ProjectDocument]:
        """Return Projects accessible to one User."""

        return list(self.projects_by_user_id.get(user_id, []))

    async def get_project(self, *, project_id: str) -> ProjectDocument:
        """Return one Project accessible to the test User."""

        for projects in self.projects_by_user_id.values():
            for project in projects:
                if project.id == project_id:
                    return project
        raise RuntimeError('Project not found.')

    async def update_project(
        self,
        *,
        project: ProjectDocument,
    ) -> ProjectDocument:
        """Replace stored Project metadata."""

        for projects in self.projects_by_user_id.values():
            for index, current in enumerate(projects):
                if current.id == project.id:
                    projects[index] = project
                    return project
        raise RuntimeError('Project not found.')

class FakeLinkedServiceService:
    """Provide the validation collaborator required by ProjectService."""

    async def require_available_selection(
        self,
        *,
        project_id: str,
        service_id: str,
        model_id: str,
    ) -> None:
        """Accept all model selections in route tests."""


def build_client() -> TestClient:
    """Build an application for User-owned Project routes."""

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
    app.state.project_controller = ProjectController(
        service=ProjectService(
            repository=InMemoryProjectRepository(),
            tenant_service=TenantService(
                repository=FakeTenantRepository([
                    ProjectMembership(
                        user_id='user-1',
                        project_id='project-1',
                        is_default=True,
                    ),
                ]),
            ),
            linked_service_service=FakeLinkedServiceService(),  # type: ignore[arg-type]
            user_service=user_service,
            id_factory=lambda: 'project-1',
            clock=lambda: datetime(2026, 8, 26, 10, 0, tzinfo=UTC),
        ),
    )
    register_exception_handlers(app)
    app.include_router(router, prefix='/api/v1')
    return TestClient(app)


def test_create_then_list_returns_a_user_owned_project() -> None:
    """A registered User can create and list its owned Project."""

    client = build_client()
    headers = {'X-User-ID': 'user-1'}

    created = client.post('/api/v1/projects', headers=headers, json={'name': 'Acme'})
    listed = client.get('/api/v1/projects', headers=headers)

    assert created.status_code == 201
    assert listed.status_code == 200
    assert created.json()['id'] == 'project-1'
    assert listed.json() == [created.json()]


def test_create_requires_a_registered_user() -> None:
    """An unregistered identity cannot create an owned Project."""

    response = build_client().post(
        '/api/v1/projects',
        headers={'X-User-ID': 'unknown-user'},
        json={'name': 'Acme'},
    )

    assert response.status_code == 404
    assert response.json()['error']['code'] == 'user_not_found'


def test_describe_and_patch_use_the_project_resource_path() -> None:
    """Project detail routes expose and update one accessible Project."""

    client = build_client()
    headers = {'X-User-ID': 'user-1'}
    client.post('/api/v1/projects', headers=headers, json={'name': 'Acme'})

    described = client.get('/api/v1/projects/project-1', headers=headers)
    updated = client.patch(
        '/api/v1/projects/project-1',
        headers=headers,
        json={'name': 'Acme Platform'},
    )

    assert described.status_code == 200
    assert described.json()['name'] == 'Acme'
    assert updated.status_code == 200
    assert updated.json()['name'] == 'Acme Platform'


def test_patch_requires_a_project_name() -> None:
    """Project metadata cannot be patched with an empty request."""

    response = build_client().patch(
        '/api/v1/projects/project-1',
        headers={'X-User-ID': 'user-1'},
        json={},
    )

    assert response.status_code == 422
