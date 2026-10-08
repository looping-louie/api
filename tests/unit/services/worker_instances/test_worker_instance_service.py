"""Tests for Worker registration and Project enablement."""

from datetime import UTC, datetime

import pytest

from src.app.models.worker import WorkerHarnessCapability
from src.app.models.worker_instance import (
    WorkerInstanceDocument,
    WorkerProjectEnablementDocument,
)
from src.app.services.shared.tenant import (
    ProjectMembership,
    TenantAccessDeniedError,
    TenantService,
)
from src.app.services.worker_instances import (
    WorkerInstanceNotFoundError,
    WorkerInstanceService,
)
from tests.fakes.tenant_repository import FakeTenantRepository


class InMemoryWorkerInstanceRepository:
    """Store Workers and their Project enablements for service tests."""

    def __init__(self) -> None:
        """Initialize empty Worker and enablement storage."""

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

    async def enable_project(
        self,
        document: WorkerProjectEnablementDocument,
    ) -> WorkerProjectEnablementDocument:
        """Store one Project enablement."""

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


def build_service(
    *,
    tenant_service: TenantService,
) -> tuple[WorkerInstanceService, InMemoryWorkerInstanceRepository]:
    """Build a Worker lifecycle service with deterministic dependencies."""

    repository = InMemoryWorkerInstanceRepository()
    service = WorkerInstanceService(
        repository=repository,
        tenant_service=tenant_service,
        id_factory=lambda: 'worker-1',
        clock=lambda: datetime(2026, 10, 6, tzinfo=UTC),
    )
    return service, repository


@pytest.mark.asyncio
async def test_worker_can_be_enabled_for_multiple_accessible_projects() -> None:
    """A caller may assign one Worker to each Project they can access."""

    tenant_service = TenantService(repository=FakeTenantRepository([
        ProjectMembership(
            user_id='user-1',
            project_id='project-a',
            is_default=True,
        ),
        ProjectMembership(user_id='user-1', project_id='project-b'),
    ]))
    service, repository = build_service(tenant_service=tenant_service)

    worker = await service.register(
        user_id='user-1',
        project_id='project-a',
        harnesses=(WorkerHarnessCapability(kind='codex_cli'),),
    )
    await service.enable_project(
        user_id='user-1',
        worker_instance_id=worker.id,
        project_id='project-b',
    )

    assert [enablement.project_id for enablement in repository.enablements] == [
        'project-a',
        'project-b',
    ]
    assert worker.owner_user_id == 'user-1'


@pytest.mark.asyncio
async def test_worker_cannot_be_enabled_for_an_inaccessible_project() -> None:
    """A Worker owner needs access to assign it to another Project."""

    tenant_service = TenantService(repository=FakeTenantRepository([
        ProjectMembership(
            user_id='user-1',
            project_id='project-a',
            is_default=True,
        ),
    ]))
    service, repository = build_service(tenant_service=tenant_service)
    worker = await service.register(
        user_id='user-1',
        project_id='project-a',
        harnesses=(),
    )

    with pytest.raises(TenantAccessDeniedError):
        await service.enable_project(
            user_id='user-1',
            worker_instance_id=worker.id,
            project_id='project-b',
        )

    assert [enablement.project_id for enablement in repository.enablements] == [
        'project-a',
    ]


@pytest.mark.asyncio
async def test_worker_detail_is_limited_to_its_owner() -> None:
    """A Worker cannot be described by a User who does not own it."""

    tenant_service = TenantService(repository=FakeTenantRepository([]))
    service, repository = build_service(tenant_service=tenant_service)
    repository.workers['worker-1'] = WorkerInstanceDocument(
        id='worker-1',
        owner_user_id='user-1',
        registered_at=datetime(2026, 10, 6, tzinfo=UTC),
        last_heartbeat_at=datetime(2026, 10, 6, tzinfo=UTC),
        harnesses=(),
    )

    with pytest.raises(WorkerInstanceNotFoundError):
        await service.get_for_user(
            user_id='user-2',
            worker_instance_id='worker-1',
        )