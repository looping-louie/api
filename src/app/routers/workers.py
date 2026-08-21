"""REST routes for workspace runtime worker registration."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from src.app.controllers.worker import WorkerController
from src.app.schemas.worker import WorkerResponse

from .dependencies import RequestContext, get_request_context, get_worker_controller


router = APIRouter(prefix='/workers', tags=['Workers'])
ContextDependency = Annotated[RequestContext, Depends(get_request_context)]
ControllerDependency = Annotated[WorkerController, Depends(get_worker_controller)]
WorkerIdPath = Annotated[str, Path(min_length=1, description='Runtime worker identifier.')]


@router.put(
    '/{worker_id}',
    response_model=WorkerResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Register worker',
)
async def register_worker(
    worker_id: WorkerIdPath,
    context: ContextDependency,
    controller: ControllerDependency,
) -> WorkerResponse:
    """Create or refresh one runtime worker registration."""

    return await controller.register(
        user_id=context.user_id,
        worker_id=worker_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    '/{worker_id}/heartbeat',
    response_model=WorkerResponse,
    summary='Heartbeat worker',
)
async def heartbeat_worker(
    worker_id: WorkerIdPath,
    context: ContextDependency,
    controller: ControllerDependency,
) -> WorkerResponse:
    """Refresh one registered runtime worker's liveness signal."""

    return await controller.heartbeat(
        user_id=context.user_id,
        worker_id=worker_id,
        requested_workspace_id=context.requested_workspace_id,
    )