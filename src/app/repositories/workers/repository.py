"""Persistence protocol for workspace worker registration."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.app.models.worker import WorkerDocument


class WorkerRepository(Protocol):
    """Persist worker identities and their liveness heartbeats."""

    async def create(self, document: WorkerDocument) -> WorkerDocument:
        """Persist one new workspace-scoped worker identity."""
        raise NotImplementedError

    async def heartbeat(
        self,
        *,
        workspace_id: str,
        worker_id: str,
        occurred_at: datetime,
    ) -> WorkerDocument | None:
        """Refresh a registered worker's liveness timestamp."""
        raise NotImplementedError

    async def is_active(
        self,
        *,
        workspace_id: str,
        worker_id: str,
        active_since: datetime,
    ) -> bool:
        """Return whether a worker sent a recent heartbeat."""
        raise NotImplementedError
