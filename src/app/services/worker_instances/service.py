"""Application service for global Worker registration and Project enablement."""

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Mapping

from src.app.models.worker import (
    WorkerHarnessCapability,
    WorkerReadinessDocument,
)
from src.app.models.worker_instance import (
    WorkerInstanceDocument,
    WorkerInstanceProjectDocument,
    WorkerProjectEnablementDocument,
)
from src.app.repositories.worker_instances import WorkerInstanceRepository
from src.app.services.shared.tenant import TenantService
GLOBAL_WORKER_ACTIVE_CLAIM_LIMIT = 1
WORKER_HEARTBEAT_TIMEOUT = timedelta(minutes=2)


class WorkerUnavailableError(Exception):
    """Raised when a global Worker cannot claim work for a Project."""

    def __init__(self, worker_id: str) -> None:
        """Store the unavailable Worker identifier."""

        super().__init__(f"Worker '{worker_id}' is not actively registered.")
        self.worker_id = worker_id


class WorkerHarnessUnavailableError(Exception):
    """Raised when a global Worker lacks a Pipeline Harness capability."""

    def __init__(self, worker_id: str) -> None:
        """Store the incompatible Worker identifier."""

        super().__init__(f"Worker '{worker_id}' lacks the required Harness.")
        self.worker_id = worker_id


class WorkerCapacityUnavailableError(Exception):
    """Raised when a global Worker already holds its active claim limit."""

    def __init__(self, worker_id: str) -> None:
        """Store the saturated Worker identifier."""

        super().__init__(f"Worker '{worker_id}' has no remaining claim capacity.")
        self.worker_id = worker_id

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

    async def require_capable(
        self,
        *,
        project_id: str,
        worker_id: str,
        harness: Mapping[str, object],
    ) -> None:
        """Reject global Workers that cannot claim work for one Project."""

        normalized_worker_id = _require_text(worker_id)
        worker = await self._repository.get_enabled(
            worker_instance_id=normalized_worker_id,
            project_id=project_id,
        )
        if (
            worker is None
            or worker.last_heartbeat_at < self._clock() - WORKER_HEARTBEAT_TIMEOUT
        ):
            raise WorkerUnavailableError(normalized_worker_id)
        if not any(candidate.matches(harness) for candidate in worker.harnesses):
            raise WorkerHarnessUnavailableError(normalized_worker_id)

    async def readiness(
        self,
        *,
        project_id: str,
        harness: Mapping[str, object],
    ) -> WorkerReadinessDocument:
        """Summarize enabled global Workers for one Project and Harness."""

        return await self._repository.readiness(
            project_id=project_id,
            active_since=self._clock() - WORKER_HEARTBEAT_TIMEOUT,
            harness=harness,
        )

    async def exists(self, *, worker_id: str) -> bool:
        """Return whether an ID belongs to a globally registered Worker."""

        return await self._repository.get(
            worker_instance_id=_require_text(worker_id),
        ) is not None

    async def list_for_project(
        self,
        *,
        user_id: str,
        requested_project_id: str | None,
    ) -> tuple[WorkerInstanceProjectDocument, ...]:
        """List global Workers the caller may inspect for one Project."""

        project = await self._tenant_service.resolve(
            user_id=user_id,
            requested_project_id=requested_project_id,
        )
        return await self._repository.list_enabled(project_id=project.project_id)

    async def get_for_project(
        self,
        *,
        user_id: str,
        requested_project_id: str | None,
        worker_instance_id: str,
    ) -> WorkerInstanceProjectDocument:
        """Return one global Worker enabled for the caller's selected Project."""

        project = await self._tenant_service.resolve(
            user_id=user_id,
            requested_project_id=requested_project_id,
        )
        worker_id = _require_text(worker_instance_id)
        worker = await self._repository.get_enabled_project(
            worker_instance_id=worker_id,
            project_id=project.project_id,
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
