"""Tests for workspace worker registration and liveness admission."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.app.models.worker import WorkerDocument
from src.app.services.workers import (
    WorkerHarnessUnavailableError,
    WorkerService,
    WorkerUnavailableError,
)
from src.app.services.shared.tenant import TenantService


class InMemoryWorkerRepository:
    """Store workers for worker service lifecycle tests."""

    def __init__(self) -> None:
        """Initialize worker storage keyed by workspace and identity."""

        self.documents: dict[tuple[str, str], WorkerDocument] = {}

    async def create(self, document: WorkerDocument) -> WorkerDocument:
        """Insert one newly provisioned worker registration."""

        self.documents[(document.workspace_id, document.id)] = document
        return document

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
            harnesses=current.harnesses,
        )
        self.documents[(workspace_id, worker_id)] = updated
        return updated

    async def get(
        self,
        *,
        workspace_id: str,
        worker_id: str,
    ) -> WorkerDocument | None:
        """Return one stored Worker capability registration."""

        return self.documents.get((workspace_id, worker_id))

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
        id_factory=lambda: 'worker-1',
        clock=lambda: now,
    )

    registered = await service.create(user_id='user-1')
    heartbeated = await service.heartbeat(user_id='user-1', worker_id='worker-1')
    await service.require_active(workspace_id='workspace-1', worker_id='worker-1')

    assert registered == heartbeated


@pytest.mark.asyncio
async def test_worker_harness_admission_requires_an_advertised_capability(
    tenant_service: TenantService,
) -> None:
    """Only an advertised Harness capability admits a Pipeline claim."""

    now = datetime(2026, 8, 21, tzinfo=UTC)
    repository = InMemoryWorkerRepository()
    service = WorkerService(
        repository=repository,
        tenant_service=tenant_service,
        id_factory=lambda: 'worker-1',
        clock=lambda: now,
    )
    registered = await service.create(user_id='user-1')

    await service.require_harness(
        workspace_id='workspace-1',
        worker_id=registered.id,
        harness={'kind': 'louie', 'version': 'v1', 'config': {}},
    )

    empty_capability_service = WorkerService(
        repository=repository,
        tenant_service=tenant_service,
        id_factory=lambda: 'worker-2',
        clock=lambda: now,
    )
    empty_worker = await empty_capability_service.create(
        user_id='user-1',
        harnesses=(),
    )

    with pytest.raises(WorkerHarnessUnavailableError):
        await empty_capability_service.require_harness(
            workspace_id='workspace-1',
            worker_id=empty_worker.id,
            harness={'kind': 'louie', 'version': 'v1', 'config': {}},
        )


@pytest.mark.asyncio
async def test_missing_worker_cannot_claim(tenant_service: TenantService) -> None:
    """A worker without registration cannot satisfy claim admission."""

    service = WorkerService(
        repository=InMemoryWorkerRepository(),
        tenant_service=tenant_service,
        id_factory=lambda: 'worker-1',
        clock=lambda: datetime(2026, 8, 21, tzinfo=UTC) + timedelta(minutes=3),
    )

    with pytest.raises(WorkerUnavailableError):
        await service.require_active(workspace_id='workspace-1', worker_id='worker-1')
