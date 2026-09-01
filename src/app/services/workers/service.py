"""Application service for worker registration and liveness admission."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Mapping

from src.app.models.worker import (
    WorkerDocument,
    WorkerHarnessCapability,
    WorkerReadinessDocument,
    default_worker_harnesses,
)
from src.app.repositories.workers import WorkerRepository
from src.app.services.shared.tenant import TenantService


WORKER_HEARTBEAT_TIMEOUT = timedelta(minutes=2)


class WorkerNotFoundError(Exception):
    """Raised when a heartbeat targets an unregistered worker."""

    def __init__(self, worker_id: str) -> None:
        """Store the absent worker identity."""

        super().__init__(f"Worker '{worker_id}' was not found.")
        self.worker_id = worker_id


class WorkerUnavailableError(Exception):
    """Raised when a runtime tries to claim without a current heartbeat."""

    def __init__(self, worker_id: str) -> None:
        """Store the unavailable worker identity."""

        super().__init__(f"Worker '{worker_id}' is not actively registered.")
        self.worker_id = worker_id


class WorkerHarnessUnavailableError(Exception):
    """Raised when an active Worker lacks a Pipeline's Harness capability."""

    def __init__(self, worker_id: str) -> None:
        """Store the incompatible Worker identifier."""

        super().__init__(f"Worker '{worker_id}' lacks the required Harness.")
        self.worker_id = worker_id


class WorkerService:
    """Coordinate durable worker registration and heartbeat liveness."""

    def __init__(
        self,
        *,
        repository: WorkerRepository,
        tenant_service: TenantService,
        id_factory: Callable[[], str],
        clock: Callable[[], datetime],
    ) -> None:
        """Store worker persistence and workspace access dependencies."""

        self._repository = repository
        self._tenant_service = tenant_service
        self._id_factory = id_factory
        self._clock = clock

    async def create(
        self,
        *,
        user_id: str,
        harnesses: tuple[WorkerHarnessCapability, ...] | None = None,
        requested_project_id: str | None = None,
    ) -> WorkerDocument:
        """Provision one API-owned worker identity in the selected workspace."""

        workspace = await self._tenant_service.resolve(
            user_id=user_id,
            requested_project_id=requested_project_id,
        )
        now = self._clock()
        return await self._repository.create(WorkerDocument(
            id=self._id_factory(),
            project_id=workspace.project_id,
            registered_at=now,
            last_heartbeat_at=now,
            harnesses=(
                harnesses
                if harnesses is not None
                else default_worker_harnesses()
            ),
        ))

    async def heartbeat(
        self,
        *,
        user_id: str,
        worker_id: str,
        harnesses: tuple[WorkerHarnessCapability, ...] | None = None,
        requested_project_id: str | None = None,
    ) -> WorkerDocument:
        """Record a liveness signal for an existing workspace worker."""

        workspace = await self._tenant_service.resolve(
            user_id=user_id,
            requested_project_id=requested_project_id,
        )
        worker = await self._repository.heartbeat(
            project_id=workspace.project_id,
            worker_id=_require_text(worker_id),
            occurred_at=self._clock(),
            harnesses=harnesses,
        )
        if worker is None:
            raise WorkerNotFoundError(worker_id)
        return worker

    async def require_active(self, *, project_id: str, worker_id: str) -> None:
        """Reject claims from workers without a current registration heartbeat."""

        if not await self._repository.is_active(
            project_id=project_id,
            worker_id=_require_text(worker_id),
            active_since=self._clock() - WORKER_HEARTBEAT_TIMEOUT,
        ):
            raise WorkerUnavailableError(worker_id)

    async def require_harness(
        self,
        *,
        project_id: str,
        worker_id: str,
        harness: Mapping[str, object],
    ) -> None:
        """Reject active Workers that do not advertise an exact Harness match."""

        normalized_worker_id = _require_text(worker_id)
        worker = await self._repository.get(
            project_id=project_id,
            worker_id=normalized_worker_id,
        )
        if worker is None or not any(
            candidate.kind == harness.get('kind')
            and candidate.version == harness.get('version')
            and dict(candidate.config) == harness.get('config')
            for candidate in worker.harnesses
        ):
            raise WorkerHarnessUnavailableError(normalized_worker_id)

    async def readiness(
        self,
        *,
        project_id: str,
        harness: Mapping[str, object],
    ) -> WorkerReadinessDocument:
        """Summarize active workers that advertise one exact Harness."""

        return await self._repository.readiness(
            project_id=project_id,
            active_since=self._clock() - WORKER_HEARTBEAT_TIMEOUT,
            harness=harness,
        )


def _require_text(value: str) -> str:
    """Normalize one required worker identifier."""

    normalized = value.strip()
    if not normalized:
        raise ValueError('worker_id must be non-empty.')
    return normalized
