"""REST routes for workspace runtime worker registration."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from src.app.controllers.worker_instances import WorkerInstanceController
from src.app.schemas.worker import (
    WorkerHeartbeatRequest,
    WorkerInstanceCreateRequest,
    WorkerInstanceProjectResponse,
    WorkerProjectEnablementResponse,
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
ProjectIdPath = Annotated[str, Path(min_length=1, description='Project identifier.')]
ProjectIdQuery = Annotated[str, Query(min_length=1, description='Project used to filter enabled Workers.')]


@router.get(
    '',
    response_model=list[WorkerInstanceProjectResponse],
    summary='List Workers for Project',
)
async def list_worker_instances(
    context: ContextDependency,
    controller: InstanceControllerDependency,
    project_id: ProjectIdQuery,
) -> list[WorkerInstanceProjectResponse]:
    """List Workers enabled for the requested Project."""

    return await controller.list_for_project(
        user_id=context.user_id,
        project_id=project_id,
    )


@router.get(
    '/{worker_id}',
    response_model=WorkerInstanceProjectResponse,
    summary='Describe Worker for Project',
)
async def get_worker_instance(
    worker_id: WorkerIdPath,
    context: ContextDependency,
    controller: InstanceControllerDependency,
) -> WorkerInstanceProjectResponse:
    """Describe one Worker enabled for the selected Project."""

    return await controller.get_for_project(
        user_id=context.user_id,
        project_id=context.requested_project_id,
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
    '/{worker_id}/projects/{project_id}',
    response_model=WorkerProjectEnablementResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Enable worker for project',
)
async def enable_worker_instance_project(
    worker_id: WorkerIdPath,
    project_id: ProjectIdPath,
    context: ContextDependency,
    controller: InstanceControllerDependency,
) -> WorkerProjectEnablementResponse:
    """Authorize one Worker to claim work for one Project."""

    return await controller.enable_project(
        user_id=context.user_id,
        worker_id=worker_id,
        project_id=project_id,
    )


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
        requested_project_id=context.requested_project_id,
    )
