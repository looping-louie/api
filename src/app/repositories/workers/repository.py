"""Persistence protocol for workspace worker registration."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping, Protocol

from src.app.models.worker import (
    WorkerDocument,
    WorkerHarnessCapability,
    WorkerReadinessDocument,
)


class WorkerRepository(Protocol):
    """Persist worker identities and their liveness heartbeats."""

    async def create(self, document: WorkerDocument) -> WorkerDocument:
        """Persist one new workspace-scoped worker identity."""
        raise NotImplementedError

    async def get(
        self,
        *,
        project_id: str,
        worker_id: str,
    ) -> WorkerDocument | None:
        """Return one persisted Worker and its declared capabilities."""
        raise NotImplementedError

    async def heartbeat(
        self,
        *,
        project_id: str,
        worker_id: str,
        occurred_at: datetime,
        harnesses: tuple[WorkerHarnessCapability, ...] | None = None,
    ) -> WorkerDocument | None:
        """Refresh liveness and optionally replace observed capabilities."""
        raise NotImplementedError

    async def is_active(
        self,
        *,
        project_id: str,
        worker_id: str,
        active_since: datetime,
    ) -> bool:
        """Return whether a worker sent a recent heartbeat."""
        raise NotImplementedError

    async def readiness(
        self,
        *,
        project_id: str,
        active_since: datetime,
        harness: Mapping[str, object],
    ) -> WorkerReadinessDocument:
        """Summarize workspace worker liveness and exact Harness matches."""
        raise NotImplementedError
