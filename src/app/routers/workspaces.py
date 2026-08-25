"""REST routes for workspace execution defaults."""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.app.controllers.workspace import WorkspaceController
from src.app.schemas.workspace import (
    WorkspaceDefaultsReplaceRequest,
    WorkspaceDefaultsResponse,
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


@router.get('/defaults', response_model=WorkspaceDefaultsResponse, summary='Get workspace defaults')
async def get_workspace_defaults(
    context: ContextDependency,
    controller: ControllerDependency,
) -> WorkspaceDefaultsResponse:
    """Return optional execution defaults for the selected workspace."""

    return await controller.get_defaults(
        user_id=context.user_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.put('/defaults', response_model=WorkspaceDefaultsResponse, summary='Replace workspace defaults')
async def replace_workspace_defaults(
    payload: WorkspaceDefaultsReplaceRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> WorkspaceDefaultsResponse:
    """Replace optional execution defaults for the selected workspace."""

    return await controller.replace_defaults(
        user_id=context.user_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )
