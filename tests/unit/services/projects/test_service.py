"""Tests for Project operations."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.app.models.user import UserDocument
from src.app.models.project import ProjectDocument
from src.app.services.projects import ProjectService
from src.app.services.shared.tenant import TenantService, ProjectMembership
from tests.fakes.tenant_repository import FakeTenantRepository


class FakeProjectRepository:
    """Store Projects in memory for service tests."""

    def __init__(self) -> None:
        """Initialize an empty Project store."""

        self.projects_by_user_id: dict[str, list[ProjectDocument]] = {}

    async def create(
        self,
        *,
        project: ProjectDocument,
        owner_id: str,
    ) -> ProjectDocument:
        """Store a Project in its owner's collection."""

        self.projects_by_user_id.setdefault(owner_id, []).append(project)
        return project

    async def list_for_user(self, *, user_id: str) -> list[ProjectDocument]:
        """Return Projects stored for one User."""

        return list(self.projects_by_user_id.get(user_id, []))

    async def get_project(self, *, project_id: str) -> ProjectDocument:
        """Return a stored Project visible through any User collection."""

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
    """Capture model-target validation requests."""

    def __init__(self) -> None:
        """Initialize an empty validation-call log."""

        self.calls: list[tuple[str, str, str]] = []

    async def require_available_selection(
        self,
        *,
        workspace_id: str,
        service_id: str,
        model_id: str,
    ) -> None:
        """Record the selection requested for validation."""

        self.calls.append((workspace_id, service_id, model_id))


class FakeUserService:
    """Record profile lookups required before Project operations."""

    def __init__(self) -> None:
        """Initialize the User lookup log."""

        self.user_ids: list[str] = []

    async def get(self, *, user_id: str) -> UserDocument:
        """Return a durable profile for the requested User."""

        self.user_ids.append(user_id)
        timestamp = datetime(2026, 8, 25, tzinfo=timezone.utc)
        return UserDocument(
            id=user_id,
            created_at=timestamp,
            updated_at=timestamp,
        )


def build_service(
    *,
    repository: FakeProjectRepository,
    linked_service_service: FakeLinkedServiceService,
    user_service: FakeUserService,
) -> ProjectService:
    """Build the service for one default Project membership."""

    tenant_service = TenantService(
        repository=FakeTenantRepository(
            [
                ProjectMembership(
                    user_id='user-1',
                    workspace_id='project-1',
                    is_default=True,
                ),
            ],
        ),
    )
    return ProjectService(
        repository=repository,
        tenant_service=tenant_service,
        linked_service_service=linked_service_service,  # type: ignore[arg-type]
        user_service=user_service,  # type: ignore[arg-type]
        id_factory=lambda: 'project-created',
        clock=lambda: datetime(2026, 8, 25, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_create_assigns_project_to_the_requesting_user() -> None:
    """Project creation verifies the User and stores its owned Project."""

    repository = FakeProjectRepository()
    user_service = FakeUserService()
    service = build_service(
        repository=repository,
        linked_service_service=FakeLinkedServiceService(),
        user_service=user_service,
    )

    project = await service.create(user_id='user-1', name='Acme')

    assert user_service.user_ids == ['user-1']
    assert project.id == 'project-created'
    assert repository.projects_by_user_id['user-1'] == [project]


@pytest.mark.asyncio
async def test_list_for_user_returns_only_its_projects() -> None:
    """Project listings are scoped to the requesting User."""

    repository = FakeProjectRepository()
    user_service = FakeUserService()
    service = build_service(
        repository=repository,
        linked_service_service=FakeLinkedServiceService(),
        user_service=user_service,
    )
    await service.create(user_id='user-1', name='Acme')
    repository.projects_by_user_id['user-2'] = [
        ProjectDocument(
            id='project-other',
            name='Other',
            created_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
            updated_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
        ),
    ]

    projects = await service.list_for_user(user_id='user-1')

    assert user_service.user_ids == ['user-1', 'user-1']
    assert [project.id for project in projects] == ['project-created']


@pytest.mark.asyncio
async def test_update_changes_project_name_and_timestamp() -> None:
    """Project updates preserve identity and replace mutable metadata."""

    repository = FakeProjectRepository()
    service = build_service(
        repository=repository,
        linked_service_service=FakeLinkedServiceService(),
        user_service=FakeUserService(),
    )
    repository.projects_by_user_id['user-1'] = [
        ProjectDocument(
            id='project-1',
            name='Acme',
            created_at=datetime(2026, 8, 24, tzinfo=timezone.utc),
            updated_at=datetime(2026, 8, 24, tzinfo=timezone.utc),
        ),
    ]

    updated = await service.update(
        user_id='user-1',
        project_id='project-1',
        name='Acme Platform',
    )

    assert updated.id == 'project-1'
    assert updated.name == 'Acme Platform'
    assert updated.updated_at == datetime(2026, 8, 25, tzinfo=timezone.utc)
