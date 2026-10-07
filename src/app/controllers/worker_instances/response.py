"""Global Worker HTTP response mapping."""

from datetime import datetime

from src.app.models.worker_instance import (
    WorkerInstanceDocument,
    WorkerInstanceProjectDocument,
    WorkerProjectEnablementDocument,
)
from src.app.schemas.worker import (
    WorkerHarnessCapabilityResponse,
    WorkerInstanceProjectResponse,
    WorkerProjectEnablementResponse,
    WorkerResponse,
)
from src.app.services.workers import WORKER_HEARTBEAT_TIMEOUT


def worker_instance_response(worker: WorkerInstanceDocument) -> WorkerResponse:
    """Map one global Worker to its public identity representation."""

    return WorkerResponse(
        id=worker.id,
        registered_at=worker.registered_at,
        last_heartbeat_at=worker.last_heartbeat_at,
        harnesses=[
            WorkerHarnessCapabilityResponse(
                kind=harness.kind,
                version=harness.version,
                config=dict(harness.config),
            )
            for harness in worker.harnesses
        ],
    )


def worker_project_enablement_response(
    enablement: WorkerProjectEnablementDocument,
) -> WorkerProjectEnablementResponse:
    """Map one global Worker's Project authorization to its HTTP response."""

    return WorkerProjectEnablementResponse(
        worker_id=enablement.worker_instance_id,
        project_id=enablement.project_id,
        enabled_at=enablement.enabled_at,
    )


def worker_instance_project_response(
    document: WorkerInstanceProjectDocument,
    *,
    observed_at: datetime,
    active_claims: int,
    capacity: int,
) -> WorkerInstanceProjectResponse:
    """Map one Project-authorized Worker with server-calculated liveness."""

    worker = document.worker
    return WorkerInstanceProjectResponse(
        id=worker.id,
        registered_at=worker.registered_at,
        last_heartbeat_at=worker.last_heartbeat_at,
        harnesses=[
            WorkerHarnessCapabilityResponse(
                kind=harness.kind,
                version=harness.version,
                config=dict(harness.config),
            )
            for harness in worker.harnesses
        ],
        enabled_at=document.enablement.enabled_at,
        active=(
            worker.last_heartbeat_at
            >= observed_at - WORKER_HEARTBEAT_TIMEOUT
        ),
        active_claims=active_claims,
        capacity=capacity,
    )
