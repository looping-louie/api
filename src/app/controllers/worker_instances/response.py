"""Global Worker HTTP response mapping."""

from src.app.models.worker_instance import (
    WorkerInstanceDocument,
    WorkerProjectEnablementDocument,
)
from src.app.schemas.worker import (
    WorkerHarnessCapabilityResponse,
    WorkerProjectEnablementResponse,
    WorkerResponse,
)


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