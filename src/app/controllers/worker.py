"""HTTP controller for workspace runtime worker registration."""

from src.app.models.worker import WorkerDocument, WorkerHarnessCapability
from src.app.schemas.worker import (
    WorkerCreateRequest,
    WorkerHarnessCapabilityResponse,
    WorkerResponse,
)
from src.app.services.workers import WorkerService


class WorkerController:
    """Translate worker registration HTTP operations into service calls."""

    def __init__(self, *, worker_service: WorkerService) -> None:
        """Store the worker registration application service."""

        self._worker_service = worker_service

    async def create(
        self,
        *,
        user_id: str,
        payload: WorkerCreateRequest | None = None,
        requested_workspace_id: str | None = None,
    ) -> WorkerResponse:
        """Provision one API-owned workspace worker identity."""

        return self._response(await self._worker_service.create(
            user_id=user_id,
            harnesses=(
                tuple(
                    WorkerHarnessCapability(
                        kind=harness.kind,
                        version=harness.version,
                        config=dict(harness.config),
                    )
                    for harness in payload.harnesses
                )
                if payload is not None
                else None
            ),
            requested_workspace_id=requested_workspace_id,
        ))

    async def heartbeat(
        self,
        *,
        user_id: str,
        worker_id: str,
        requested_workspace_id: str | None = None,
    ) -> WorkerResponse:
        """Record one liveness heartbeat for a registered worker."""

        return self._response(await self._worker_service.heartbeat(
            user_id=user_id,
            worker_id=worker_id,
            requested_workspace_id=requested_workspace_id,
        ))

    @staticmethod
    def _response(worker: WorkerDocument) -> WorkerResponse:
        """Map one worker document to its public representation."""

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
