"""REST routes for workspace runtime worker registration."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, status

from src.app.controllers.worker import WorkerController
from src.app.schemas.worker import WorkerCreateRequest, WorkerResponse

from .dependencies import RequestContext, get_request_context, get_worker_controller


router = APIRouter(prefix='/workers', tags=['Workers'])
ContextDependency = Annotated[RequestContext, Depends(get_request_context)]
ControllerDependency = Annotated[WorkerController, Depends(get_worker_controller)]
WorkerIdPath = Annotated[str, Path(min_length=1, description='Runtime worker identifier.')]


@router.post(
    '',
    response_model=WorkerResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Create worker',
)
async def create_worker(
    context: ContextDependency,
    controller: ControllerDependency,
    payload: Annotated[WorkerCreateRequest | None, Body()] = None,
) -> WorkerResponse:
    """Create one API-owned runtime worker identity."""

    return await controller.create(
        user_id=context.user_id,
        payload=payload,
        requested_project_id=context.requested_project_id,
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
        requested_project_id=context.requested_project_id,
    )
