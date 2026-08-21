"""Tests for workspace worker registration and liveness admission."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.app.models.worker import WorkerDocument
from src.app.services.workers import WorkerService, WorkerUnavailableError
from src.app.services.shared.tenant import TenantService


class InMemoryWorkerRepository:
    """Store workers for worker service lifecycle tests."""

    def __init__(self) -> None:
        """Initialize worker storage keyed by workspace and identity."""

        self.documents: dict[tuple[str, str], WorkerDocument] = {}

    async def register(self, document: WorkerDocument) -> WorkerDocument:
        """Insert or refresh one worker registration."""

        current = self.documents.get((document.workspace_id, document.id))
        stored = WorkerDocument(
            id=document.id,
            workspace_id=document.workspace_id,
            registered_at=(
                current.registered_at if current is not None else document.registered_at
            ),
            last_heartbeat_at=document.last_heartbeat_at,
        )
        self.documents[(stored.workspace_id, stored.id)] = stored
        return stored

    async def heartbeat(
        self, *, workspace_id: str, worker_id: str, occurred_at: datetime,
    ) -> WorkerDocument | None:
        """Update one registered worker heartbeat."""

        current = self.documents.get((workspace_id, worker_id))
        if current is None:
            return None
        updated = WorkerDocument(
            id=current.id, workspace_id=current.workspace_id,
            registered_at=current.registered_at, last_heartbeat_at=occurred_at,
        )
        self.documents[(workspace_id, worker_id)] = updated
        return updated

    async def is_active(
        self, *, workspace_id: str, worker_id: str, active_since: datetime,
    ) -> bool:
        """Return whether the stored worker heartbeat satisfies the cutoff."""

        worker = self.documents.get((workspace_id, worker_id))
        return worker is not None and worker.last_heartbeat_at >= active_since


@pytest.mark.asyncio
async def test_registered_worker_heartbeat_admits_claims(
    tenant_service: TenantService,
) -> None:
    """Registration and a current heartbeat make one worker claim-eligible."""

    now = datetime(2026, 8, 21, tzinfo=UTC)
    repository = InMemoryWorkerRepository()
    service = WorkerService(
        repository=repository,
        tenant_service=tenant_service,
        clock=lambda: now,
    )

    registered = await service.register(user_id='user-1', worker_id='worker-1')
    heartbeated = await service.heartbeat(user_id='user-1', worker_id='worker-1')
    await service.require_active(workspace_id='workspace-1', worker_id='worker-1')

    assert registered == heartbeated


@pytest.mark.asyncio
async def test_missing_worker_cannot_claim(tenant_service: TenantService) -> None:
    """A worker without registration cannot satisfy claim admission."""

    service = WorkerService(
        repository=InMemoryWorkerRepository(),
        tenant_service=tenant_service,
        clock=lambda: datetime(2026, 8, 21, tzinfo=UTC) + timedelta(minutes=3),
    )

    with pytest.raises(WorkerUnavailableError):
        await service.require_active(workspace_id='workspace-1', worker_id='worker-1')