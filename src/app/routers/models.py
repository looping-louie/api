"""REST routes for the curated model catalog."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from src.app.catalogs.models import (
    ModelCapability,
    ModelStatus,
)
from src.app.catalogs.providers import ProviderId
from src.app.controllers.model import ModelController
from src.app.schemas.model import (
    ModelListResponse,
    ModelResponse,
)

from .dependencies import (
    RequestContext,
    get_model_controller,
    get_request_context,
)


router = APIRouter(
    prefix="/models",
    tags=["Models"],
)

ContextDependency = Annotated[
    RequestContext,
    Depends(get_request_context),
]

ControllerDependency = Annotated[
    ModelController,
    Depends(get_model_controller),
]


@router.get(
    "",
    response_model=ModelListResponse,
    summary="List models",
)
async def list_models(
    context: ContextDependency,
    controller: ControllerDependency,
    provider_id: Annotated[
        ProviderId | None,
        Query(
            description="Filter models by provider.",
        ),
    ] = None,
    capability: Annotated[
        ModelCapability | None,
        Query(
            description="Filter models by capability.",
        ),
    ] = None,
    model_status: Annotated[
        ModelStatus | None,
        Query(
            alias="status",
            description="Filter models by catalog status.",
        ),
    ] = None,
    available: Annotated[
        bool | None,
        Query(
            description="Filter by workspace availability.",
        ),
    ] = None,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=200,
            description="Search by name, vendor, family or tag.",
        ),
    ] = None,
    include_deprecated: Annotated[
        bool,
        Query(
            description="Include deprecated catalog entries.",
        ),
    ] = False,
) -> ModelListResponse:
    """List the curated model catalog and workspace availability."""

    return await controller.list(
        user_id=context.user_id,
        requested_workspace_id=context.requested_workspace_id,
        provider_id=provider_id,
        capability=capability,
        model_status=model_status,
        available=available,
        search=search,
        include_deprecated=include_deprecated,
    )


@router.get(
    "/{model_id}",
    response_model=ModelResponse,
    summary="Describe model",
)
async def describe_model(
    context: ContextDependency,
    controller: ControllerDependency,
    model_id: Annotated[
        str,
        Path(
            min_length=1,
            description="Logical model identifier.",
        ),
    ],
) -> ModelResponse:
    """Return model deployments, capabilities and availability."""

    return await controller.describe(
        user_id=context.user_id,
        model_id=model_id,
        requested_workspace_id=context.requested_workspace_id,
    )
