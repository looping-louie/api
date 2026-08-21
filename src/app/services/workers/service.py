"""Application service for worker registration and liveness admission."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from src.app.models.worker import WorkerDocument
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


class WorkerService:
    """Coordinate durable worker registration and heartbeat liveness."""

    def __init__(
        self,
        *,
        repository: WorkerRepository,
        tenant_service: TenantService,
        clock: Callable[[], datetime],
    ) -> None:
        """Store worker persistence and workspace access dependencies."""

        self._repository = repository
        self._tenant_service = tenant_service
        self._clock = clock

    async def register(
        self,
        *,
        user_id: str,
        worker_id: str,
        requested_workspace_id: str | None = None,
    ) -> WorkerDocument:
        """Create or refresh one worker registration in the selected workspace."""

        workspace = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        now = self._clock()
        return await self._repository.register(WorkerDocument(
            id=_require_text(worker_id),
            workspace_id=workspace.workspace_id,
            registered_at=now,
            last_heartbeat_at=now,
        ))

    async def heartbeat(
        self,
        *,
        user_id: str,
        worker_id: str,
        requested_workspace_id: str | None = None,
    ) -> WorkerDocument:
        """Record a liveness signal for an existing workspace worker."""

        workspace = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        worker = await self._repository.heartbeat(
            workspace_id=workspace.workspace_id,
            worker_id=_require_text(worker_id),
            occurred_at=self._clock(),
        )
        if worker is None:
            raise WorkerNotFoundError(worker_id)
        return worker

    async def require_active(self, *, workspace_id: str, worker_id: str) -> None:
        """Reject claims from workers without a current registration heartbeat."""

        if not await self._repository.is_active(
            workspace_id=workspace_id,
            worker_id=_require_text(worker_id),
            active_since=self._clock() - WORKER_HEARTBEAT_TIMEOUT,
        ):
            raise WorkerUnavailableError(worker_id)


def _require_text(value: str) -> str:
    """Normalize one required worker identifier."""

    normalized = value.strip()
    if not normalized:
        raise ValueError('worker_id must be non-empty.')
    return normalized
