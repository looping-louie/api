"""REST routes for workspace runtime worker registration."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from src.app.controllers.worker_instances import WorkerInstanceController
from src.app.schemas.worker import (
    WorkerHeartbeatRequest,
    WorkerInstanceCreateRequest,
    WorkerResponse,
)

from .dependencies import (
    RequestContext,
    get_request_context,
    get_worker_instance_controller,
)


router = APIRouter(prefix='/workers', tags=['Workers'])
ContextDependency = Annotated[RequestContext, Depends(get_request_context)]
InstanceControllerDependency = Annotated[
    WorkerInstanceController,
    Depends(get_worker_instance_controller),
]
WorkerIdPath = Annotated[str, Path(min_length=1, description='Runtime worker identifier.')]


@router.get(
    '',
    response_model=list[WorkerResponse],
    summary='List owned Workers',
)
async def list_worker_instances(
    context: ContextDependency,
    controller: InstanceControllerDependency,
) -> list[WorkerResponse]:
    """List Workers owned by the requesting User."""

    return await controller.list_for_user(user_id=context.user_id)


@router.get(
    '/{worker_id}',
    response_model=WorkerResponse,
    summary='Describe worker',
)
async def get_worker_instance(
    worker_id: WorkerIdPath,
    context: ContextDependency,
    controller: InstanceControllerDependency,
) -> WorkerResponse:
    """Describe one Worker owned by the requesting User."""

    return await controller.describe(
        user_id=context.user_id,
        worker_instance_id=worker_id,
    )


@router.post(
    '',
    response_model=WorkerResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Register worker',
)
async def create_worker_instance(
    context: ContextDependency,
    controller: InstanceControllerDependency,
    payload: WorkerInstanceCreateRequest,
) -> WorkerResponse:
    """Register one Worker and enable its initial Project."""

    return await controller.create(user_id=context.user_id, payload=payload)


@router.post(
    '/{worker_id}/heartbeat',
    response_model=WorkerResponse,
    summary='Heartbeat worker',
)
async def heartbeat_worker_instance(
    worker_id: WorkerIdPath,
    context: ContextDependency,
    controller: InstanceControllerDependency,
    payload: WorkerHeartbeatRequest,
) -> WorkerResponse:
    """Refresh one Worker's liveness and reported capabilities."""

    return await controller.heartbeat(
        user_id=context.user_id,
        worker_id=worker_id,
        payload=payload,
    )
