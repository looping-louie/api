"""REST routes for workspace execution defaults."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from src.app.catalogs.models import (
    ModelCapability,
    ModelLab,
    ModelSort,
    ModelStatus,
)
from src.app.catalogs.providers import ProviderId
from src.app.controllers.workspace import WorkspaceController, WorkspaceModelController
from src.app.schemas.model import ModelListResponse, ModelResponse
from src.app.schemas.workspace import (
    WorkspaceDefaultsReplaceRequest,
    WorkspaceDefaultsResponse,
    WorkspaceCreateRequest,
    WorkspacePatchRequest,
    WorkspaceResponse,
)

from .dependencies import (
    RequestContext,
    get_workspace_model_controller,
    get_workspace_controller,
    get_request_context,
)


router = APIRouter(prefix='/workspaces', tags=['Workspaces'])
ContextDependency = Annotated[RequestContext, Depends(get_request_context)]
ControllerDependency = Annotated[
    WorkspaceController,
    Depends(get_workspace_controller),
]
WorkspaceModelControllerDependency = Annotated[
    WorkspaceModelController,
    Depends(get_workspace_model_controller),
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
    '/{workspace_id}',
    response_model=WorkspaceResponse,
    summary='Get workspace',
)
async def get_workspace(
    workspace_id: WorkspaceIdPath,
    context: ContextDependency,
    controller: ControllerDependency,
) -> WorkspaceResponse:
    """Return one Workspace accessible to the requesting User."""

    return await controller.describe(
        user_id=context.user_id,
        workspace_id=workspace_id,
    )


@router.patch(
    '/{workspace_id}',
    response_model=WorkspaceResponse,
    summary='Update workspace',
)
async def patch_workspace(
    workspace_id: WorkspaceIdPath,
    payload: WorkspacePatchRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> WorkspaceResponse:
    """Update mutable metadata for one accessible Workspace."""

    return await controller.patch(
        user_id=context.user_id,
        workspace_id=workspace_id,
        payload=payload,
    )


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


@router.get(
    '/{workspace_id}/models',
    response_model=ModelListResponse,
    summary='List workspace models',
)
async def list_workspace_models(
    workspace_id: WorkspaceIdPath,
    context: ContextDependency,
    controller: WorkspaceModelControllerDependency,
    provider_id: Annotated[
        ProviderId | None,
        Query(description='Filter models by provider.'),
    ] = None,
    capability: Annotated[
        ModelCapability | None,
        Query(description='Filter models by capability.'),
    ] = None,
    model_status: Annotated[
        ModelStatus | None,
        Query(alias='status', description='Filter models by catalog status.'),
    ] = None,
    lab: Annotated[
        list[ModelLab] | None,
        Query(description='Filter by one or more typed lab slugs.'),
    ] = None,
    sort: Annotated[
        ModelSort | None,
        Query(description='Order the filtered model catalog.'),
    ] = None,
    offset: Annotated[
        int,
        Query(ge=0, description='Number of filtered models to skip. Page size is 24.'),
    ] = 0,
    available: Annotated[
        bool | None,
        Query(description='Filter by workspace availability.'),
    ] = None,
    search: Annotated[
        str | None,
        Query(min_length=1, max_length=200, description='Search by name, vendor, family or tag.'),
    ] = None,
    include_deprecated: Annotated[
        bool,
        Query(
            description=(
                'Include deprecated entries when status is not supplied. '
                'An explicit deprecated status always selects them.'
            ),
        ),
    ] = False,
) -> ModelListResponse:
    """List curated models and availability for one Workspace."""

    return await controller.list(
        user_id=context.user_id,
        workspace_id=workspace_id,
        provider_id=provider_id,
        capability=capability,
        model_status=model_status,
        labs=lab or (),
        sort=sort,
        offset=offset,
        available=available,
        search=search,
        include_deprecated=include_deprecated,
    )


@router.get(
    '/{workspace_id}/models/{model_id}',
    response_model=ModelResponse,
    summary='Describe workspace model',
)
async def describe_workspace_model(
    workspace_id: WorkspaceIdPath,
    model_id: Annotated[str, Path(min_length=1, description='Logical model identifier.')],
    context: ContextDependency,
    controller: WorkspaceModelControllerDependency,
) -> ModelResponse:
    """Return model offerings, capabilities, and availability for one Workspace."""

    return await controller.describe(
        user_id=context.user_id,
        workspace_id=workspace_id,
        model_id=model_id,
    )
