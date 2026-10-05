"""Tests for workspace worker registration and liveness admission."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.app.models.worker import WorkerDocument, WorkerHarnessCapability
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

        self.documents[(document.project_id, document.id)] = document
        return document

    async def heartbeat(
        self, *, project_id: str, worker_id: str, occurred_at: datetime,
        harnesses: tuple[WorkerHarnessCapability, ...] | None = None,
    ) -> WorkerDocument | None:
        """Update one registered worker heartbeat."""

        current = self.documents.get((project_id, worker_id))
        if current is None:
            return None
        updated = WorkerDocument(
            id=current.id, project_id=current.project_id,
            registered_at=current.registered_at, last_heartbeat_at=occurred_at,
            harnesses=harnesses if harnesses is not None else current.harnesses,
        )
        self.documents[(project_id, worker_id)] = updated
        return updated

    async def get(
        self,
        *,
        project_id: str,
        worker_id: str,
    ) -> WorkerDocument | None:
        """Return one stored Worker capability registration."""

        return self.documents.get((project_id, worker_id))

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

    registered = await service.create(
        user_id='user-1',
        harnesses=(WorkerHarnessCapability(kind='louie'),),
    )
    heartbeated = await service.heartbeat(
        user_id='user-1',
        worker_id='worker-1',
        harnesses=(WorkerHarnessCapability(kind='louie'),),
    )
    await service.require_capable(
        project_id='workspace-1', worker_id='worker-1',
        harness={'kind': 'louie', 'version': 'v1', 'config': {}},
    )

    assert registered == heartbeated


@pytest.mark.asyncio
async def test_heartbeat_replaces_observed_harness_capabilities(
    tenant_service: TenantService,
) -> None:
    """A heartbeat removes Codex admission when the local login is unavailable."""

    now = datetime(2026, 8, 21, tzinfo=UTC)
    repository = InMemoryWorkerRepository()
    service = WorkerService(
        repository=repository,
        tenant_service=tenant_service,
        id_factory=lambda: 'worker-1',
        clock=lambda: now,
    )
    worker = await service.create(
        user_id='user-1',
        harnesses=(
            WorkerHarnessCapability(kind='louie'),
            WorkerHarnessCapability(kind='codex_cli'),
        ),
    )

    refreshed = await service.heartbeat(
        user_id='user-1',
        worker_id=worker.id,
        harnesses=(WorkerHarnessCapability(kind='louie'),),
    )

    assert [harness.kind for harness in refreshed.harnesses] == ['louie']
    with pytest.raises(WorkerHarnessUnavailableError):
        await service.require_capable(
            project_id='workspace-1',
            worker_id=worker.id,
            harness={'kind': 'codex_cli', 'version': 'v1', 'config': {}},
        )


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
    registered = await service.create(
        user_id='user-1',
        harnesses=(WorkerHarnessCapability(kind='louie'),),
    )

    await service.require_capable(
        project_id='workspace-1',
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
        await empty_capability_service.require_capable(
            project_id='workspace-1',
            worker_id=empty_worker.id,
            harness={'kind': 'louie', 'version': 'v1', 'config': {}},
        )


@pytest.mark.asyncio
@pytest.mark.parametrize('registered', [False, True])
async def test_inactive_worker_cannot_claim(
    tenant_service: TenantService,
    registered: bool,
) -> None:
    """A missing or stale worker cannot satisfy combined claim admission."""

    now = datetime(2026, 8, 21, tzinfo=UTC)
    repository = InMemoryWorkerRepository()
    if registered:
        await WorkerService(
            repository=repository, tenant_service=tenant_service,
            id_factory=lambda: 'worker-1', clock=lambda: now,
        ).create(
            user_id='user-1',
            harnesses=(WorkerHarnessCapability(kind='louie'),),
        )
    service = WorkerService(
        repository=repository,
        tenant_service=tenant_service,
        id_factory=lambda: 'worker-1',
        clock=lambda: now + timedelta(minutes=3),
    )

    with pytest.raises(WorkerUnavailableError):
        await service.require_capable(
            project_id='workspace-1', worker_id='worker-1',
            harness={'kind': 'louie', 'version': 'v1', 'config': {}},
        )
