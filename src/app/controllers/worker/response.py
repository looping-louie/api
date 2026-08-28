"""Worker HTTP response mapping."""

from src.app.models.worker import WorkerDocument
from src.app.schemas.worker import WorkerHarnessCapabilityResponse, WorkerResponse


def worker_response(worker: WorkerDocument) -> WorkerResponse:
    """Map a Worker document to its public representation."""

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