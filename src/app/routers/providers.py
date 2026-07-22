"""RPC routes for model provider configuration."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from src.app.controllers.provider import ProviderController
from src.app.schemas.common import DeleteResponse
from src.app.schemas.providers import (
    ProviderResponse,
    ProviderSetRequest,
    ProviderTestResponse,
)

from .dependencies import (
    RequestContext,
    get_provider_controller,
    get_request_context,
)


router = APIRouter(
    prefix="/providers",
    tags=["Providers"],
)

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
    Path(
        min_length=1,
        description="Curated provider identifier.",
    ),
]


@router.get(
    "/list",
    response_model=list[ProviderResponse],
    summary="List providers",
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
    "/describe/{provider_id}",
    response_model=ProviderResponse,
    summary="Describe provider",
)
async def describe_provider(
    provider_id: ProviderIdPath,
    context: ContextDependency,
    controller: ControllerDependency,
) -> ProviderResponse:
    """Return provider metadata and configuration state."""

    return await controller.describe(
        user_id=context.user_id,
        provider_id=provider_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "/configure/{provider_id}",
    response_model=ProviderResponse,
    summary="Configure provider",
)
async def configure_provider(
    provider_id: ProviderIdPath,
    payload: ProviderSetRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> ProviderResponse:
    """Store or replace provider credentials and configuration."""

    return await controller.configure(
        user_id=context.user_id,
        provider_id=provider_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "/enable/{provider_id}",
    response_model=ProviderResponse,
    summary="Enable provider",
)
async def enable_provider(
    provider_id: ProviderIdPath,
    context: ContextDependency,
    controller: ControllerDependency,
) -> ProviderResponse:
    """Enable a previously configured provider."""

    return await controller.enable(
        user_id=context.user_id,
        provider_id=provider_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "/disable/{provider_id}",
    response_model=ProviderResponse,
    summary="Disable provider",
)
async def disable_provider(
    provider_id: ProviderIdPath,
    context: ContextDependency,
    controller: ControllerDependency,
) -> ProviderResponse:
    """Disable a provider without deleting its credentials."""

    return await controller.disable(
        user_id=context.user_id,
        provider_id=provider_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "/test/{provider_id}",
    response_model=ProviderTestResponse,
    summary="Test provider",
)
async def test_provider(
    provider_id: ProviderIdPath,
    context: ContextDependency,
    controller: ControllerDependency,
) -> ProviderTestResponse:
    """Test the stored provider configuration."""

    return await controller.test(
        user_id=context.user_id,
        provider_id=provider_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.delete(
    "/delete/{provider_id}",
    response_model=DeleteResponse,
    summary="Delete provider configuration",
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
