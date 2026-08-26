"""REST routes for workspace execution defaults."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from src.app.controllers.workspace import WorkspaceController
from src.app.schemas.workspace import (
    WorkspaceDefaultsReplaceRequest,
    WorkspaceDefaultsResponse,
    WorkspaceCreateRequest,
    WorkspaceResponse,
)

from .dependencies import (
    RequestContext,
    get_workspace_controller,
    get_request_context,
)


router = APIRouter(prefix='/workspaces', tags=['Workspaces'])
ContextDependency = Annotated[RequestContext, Depends(get_request_context)]
ControllerDependency = Annotated[
    WorkspaceController,
    Depends(get_workspace_controller),
]
WorkspaceIdPath = Annotated[str, Path(min_length=1, description='Workspace identifier.')]


@router.get('', response_model=list[WorkspaceResponse], summary='List workspaces')
async def list_workspaces(
    context: ContextDependency,
    controller: ControllerDependency,
) -> list[WorkspaceResponse]:
    """List workspaces available to the requesting user."""

    return await controller.list_for_user(user_id=context.user_id)


@router.post(
    '',
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Create workspace',
)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> WorkspaceResponse:
    """Create a workspace owned by the requesting user."""

    return await controller.create(user_id=context.user_id, payload=payload)


@router.get(
    '/{workspace_id}/defaults',
    response_model=WorkspaceDefaultsResponse,
    summary='Get workspace defaults',
)
async def get_workspace_defaults(
    workspace_id: WorkspaceIdPath,
    context: ContextDependency,
    controller: ControllerDependency,
) -> WorkspaceDefaultsResponse:
    """Return optional execution defaults for one accessible workspace."""

    return await controller.get_defaults(
        user_id=context.user_id,
        workspace_id=workspace_id,
    )


@router.put(
    '/{workspace_id}/defaults',
    response_model=WorkspaceDefaultsResponse,
    summary='Replace workspace defaults',
)
async def replace_workspace_defaults(
    workspace_id: WorkspaceIdPath,
    payload: WorkspaceDefaultsReplaceRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> WorkspaceDefaultsResponse:
    """Replace optional execution defaults for one accessible workspace."""

    return await controller.replace_defaults(
        user_id=context.user_id,
        workspace_id=workspace_id,
        payload=payload,
    )
