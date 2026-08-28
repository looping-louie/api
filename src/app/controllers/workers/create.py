"""Controller for creating Workers."""

from src.app.models.worker import WorkerHarnessCapability
from src.app.schemas.worker import WorkerCreateRequest, WorkerResponse
from src.app.services.workers import WorkerService

from .response import worker_response


class WorkerCreateController:
    """Create API-owned runtime Worker identities."""

    async def create(
        self,
        *,
        user_id: str,
        payload: WorkerCreateRequest | None = None,
        requested_project_id: str | None = None,
    ) -> WorkerResponse:
        """Provision one Worker identity and record its Harness capabilities."""

        return worker_response(await self._worker_service.create(
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
            requested_project_id=requested_project_id,
        ))

    _worker_service: WorkerService