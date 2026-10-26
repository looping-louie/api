"""REST routes for projects."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from src.app.controllers.projects import ProjectController
from src.app.controllers.worker_instances import WorkerInstanceController
from src.app.schemas.project import (
    ProjectCreateRequest,
    ProjectPatchRequest,
    ProjectResponse,
)
from src.app.schemas.shared import DeleteResponse
from src.app.schemas.worker import (
    WorkerInstanceProjectResponse,
    WorkerProjectEnablementResponse,
)

from .dependencies import (
    RequestContext,
    get_project_controller,
    get_request_context,
    get_worker_instance_controller,
)


router = APIRouter(prefix='/projects', tags=['Projects'])
ContextDependency = Annotated[RequestContext, Depends(get_request_context)]
ControllerDependency = Annotated[
    ProjectController,
    Depends(get_project_controller),
]
WorkerControllerDependency = Annotated[
    WorkerInstanceController,
    Depends(get_worker_instance_controller),
]
ProjectIdPath = Annotated[str, Path(min_length=1, description='Project identifier.')]
WorkerIdPath = Annotated[str, Path(min_length=1, description='Worker identifier.')]


@router.get('', response_model=list[ProjectResponse], summary='List projects')
async def list_projects(
    context: ContextDependency,
    controller: ControllerDependency,
) -> list[ProjectResponse]:
    """List Projects available to the requesting User."""

    return await controller.list_for_user(user_id=context.user_id)


@router.post(
    '',
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Create project',
)
async def create_project(
    payload: ProjectCreateRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> ProjectResponse:
    """Create a Project owned by the requesting User."""

    return await controller.create(user_id=context.user_id, payload=payload)


@router.get(
    '/{project_id}/workers',
    response_model=list[WorkerInstanceProjectResponse],
    summary='List Workers enabled for Project',
)
async def list_project_workers(
    project_id: ProjectIdPath,
    context: ContextDependency,
    controller: WorkerControllerDependency,
) -> list[WorkerInstanceProjectResponse]:
    """List Workers enabled for one accessible Project."""

    return await controller.list_for_project(
        user_id=context.user_id,
        project_id=project_id,
    )


@router.post(
    '/{project_id}/workers/{worker_id}',
    response_model=WorkerProjectEnablementResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Enable Worker for Project',
)
async def enable_project_worker(
    project_id: ProjectIdPath,
    worker_id: WorkerIdPath,
    context: ContextDependency,
    controller: WorkerControllerDependency,
) -> WorkerProjectEnablementResponse:
    """Authorize one Worker to claim work for one accessible Project."""

    return await controller.enable_project(
        user_id=context.user_id,
        worker_id=worker_id,
        project_id=project_id,
    )


@router.delete(
    '/{project_id}/workers/{worker_id}',
    response_model=DeleteResponse,
    summary='Disable Worker for Project',
)
async def disable_project_worker(
    project_id: ProjectIdPath,
    worker_id: WorkerIdPath,
    context: ContextDependency,
    controller: WorkerControllerDependency,
) -> DeleteResponse:
    """Prevent one Worker from claiming future work for one Project."""

    return await controller.disable_project(
        user_id=context.user_id,
        worker_id=worker_id,
        project_id=project_id,
    )


@router.get(
    '/{project_id}',
    response_model=ProjectResponse,
    summary='Get project',
)
async def get_project(
    project_id: ProjectIdPath,
    context: ContextDependency,
    controller: ControllerDependency,
) -> ProjectResponse:
    """Return one Project accessible to the requesting User."""

    return await controller.describe(
        user_id=context.user_id,
        project_id=project_id,
    )


@router.patch(
    '/{project_id}',
    response_model=ProjectResponse,
    summary='Update project',
)
async def patch_project(
    project_id: ProjectIdPath,
    payload: ProjectPatchRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> ProjectResponse:
    """Update mutable metadata for one accessible Project."""

    return await controller.patch(
        user_id=context.user_id,
        project_id=project_id,
        payload=payload,
    )
