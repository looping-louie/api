"""Application service for global Worker registration and Project enablement."""

from collections.abc import Callable
from datetime import datetime

from src.app.models.worker import WorkerHarnessCapability
from src.app.models.worker_instance import (
    WorkerInstanceDocument,
    WorkerProjectEnablementDocument,
)
from src.app.repositories.worker_instances import WorkerInstanceRepository
from src.app.services.shared.tenant import TenantService


class WorkerInstanceNotFoundError(Exception):
    """Raised when an operation targets an unregistered global Worker."""

    def __init__(self, worker_instance_id: str) -> None:
        """Store the absent Worker identity."""

        super().__init__(f"Worker '{worker_instance_id}' was not found.")
        self.worker_instance_id = worker_instance_id


class WorkerInstanceService:
    """Manage global Workers and their authorized Project assignments."""

    def __init__(
        self,
        *,
        repository: WorkerInstanceRepository,
        tenant_service: TenantService,
        id_factory: Callable[[], str],
        clock: Callable[[], datetime],
    ) -> None:
        """Store Worker persistence, Project access, and clock dependencies."""

        self._repository = repository
        self._tenant_service = tenant_service
        self._id_factory = id_factory
        self._clock = clock

    async def register(
        self,
        *,
        user_id: str,
        project_id: str,
        harnesses: tuple[WorkerHarnessCapability, ...],
    ) -> WorkerInstanceDocument:
        """Register one Worker with an authorized initial Project assignment."""

        project = await self._tenant_service.require_access(
            user_id=user_id,
            project_id=project_id,
        )
        now = self._clock()
        worker = await self._repository.create(WorkerInstanceDocument(
            id=self._id_factory(),
            registered_at=now,
            last_heartbeat_at=now,
            harnesses=harnesses,
        ))
        await self._repository.enable_project(WorkerProjectEnablementDocument(
            worker_instance_id=worker.id,
            project_id=project.project_id,
            enabled_at=now,
        ))
        return worker

    async def enable_project(
        self,
        *,
        user_id: str,
        worker_instance_id: str,
        project_id: str,
    ) -> WorkerProjectEnablementDocument:
        """Enable an existing Worker for one Project accessible to the caller."""

        project = await self._tenant_service.require_access(
            user_id=user_id,
            project_id=project_id,
        )
        worker_id = _require_text(worker_instance_id)
        if await self._repository.get(worker_instance_id=worker_id) is None:
            raise WorkerInstanceNotFoundError(worker_id)
        return await self._repository.enable_project(
            WorkerProjectEnablementDocument(
                worker_instance_id=worker_id,
                project_id=project.project_id,
                enabled_at=self._clock(),
            ),
        )

    async def heartbeat(
        self,
        *,
        user_id: str,
        worker_instance_id: str,
        harnesses: tuple[WorkerHarnessCapability, ...],
        requested_project_id: str | None = None,
    ) -> WorkerInstanceDocument:
        """Refresh one global Worker's liveness and observed Harnesses."""

        await self._tenant_service.resolve(
            user_id=user_id,
            requested_project_id=requested_project_id,
        )
        worker_id = _require_text(worker_instance_id)
        worker = await self._repository.heartbeat(
            worker_instance_id=worker_id,
            occurred_at=self._clock(),
            harnesses=harnesses,
        )
        if worker is None:
            raise WorkerInstanceNotFoundError(worker_id)
        return worker


def _require_text(value: str) -> str:
    """Normalize one required Worker identifier."""

    normalized = value.strip()
    if not normalized:
        raise ValueError('worker_instance_id must be non-empty.')
    return normalized