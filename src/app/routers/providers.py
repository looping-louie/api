"""REST routes for model provider configuration."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from src.app.controllers.provider import ProviderController
from src.app.schemas.provider import ProviderPatchRequest, ProviderResponse
from src.app.schemas.shared import DeleteResponse

from .dependencies import (
    RequestContext,
    get_provider_controller,
    get_request_context,
)


router = APIRouter(prefix="/providers", tags=["Providers"])

ContextDependency = Annotated[
    RequestContext,
    Depends(get_request_context),
]
ControllerDependency = Annotated[
    ProviderController,
    Depends(get_provider_controller),
]
ProviderIdPath = Annotated[
    str,
    Path(min_length=1, description="Curated provider identifier."),
]


@router.get(
    "",
    response_model=list[ProviderResponse],
    summary="List providers",
    deprecated=True,
)
async def list_providers(
    context: ContextDependency,
    controller: ControllerDependency,
) -> list[ProviderResponse]:
    """List supported providers and their workspace state."""

    return await controller.list(
        user_id=context.user_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.get(
    "/{provider_id}",
    response_model=ProviderResponse,
    summary="Get provider",
    deprecated=True,
)
async def get_provider(
    provider_id: ProviderIdPath,
    context: ContextDependency,
    controller: ControllerDependency,
) -> ProviderResponse:
    """Return provider metadata and configuration state."""

    return await controller.get(
        user_id=context.user_id,
        provider_id=provider_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.patch(
    "/{provider_id}",
    response_model=ProviderResponse,
    summary="Configure provider",
    deprecated=True,
)
async def patch_provider(
    provider_id: ProviderIdPath,
    payload: ProviderPatchRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> ProviderResponse:
    """Update provider credentials, base URL, or enabled state."""

    return await controller.patch(
        user_id=context.user_id,
        provider_id=provider_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.delete(
    "/{provider_id}",
    response_model=DeleteResponse,
    summary="Delete provider configuration",
    deprecated=True,
)
async def delete_provider(
    provider_id: ProviderIdPath,
    context: ContextDependency,
    controller: ControllerDependency,
) -> DeleteResponse:
    """Delete stored configuration and encrypted credentials."""

    return await controller.delete(
        user_id=context.user_id,
        provider_id=provider_id,
        requested_workspace_id=context.requested_workspace_id,
    )
