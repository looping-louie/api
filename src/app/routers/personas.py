"""REST routes for persona resources."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from src.app.catalogs.persona_skills import (
    CatalogInstructionCategory,
    CatalogInstructionSort,
    CatalogInstructionStatus,
)
from src.app.controllers.personas import PersonaController
from src.app.schemas.shared import DeleteResponse
from src.app.schemas.persona import (
    PersonaCreateRequest,
    PersonaListResponse,
    PersonaPatchRequest,
    PersonaResponse,
)

from .dependencies import (
    RequestContext,
    get_persona_controller,
    get_request_context,
)


router = APIRouter(
    prefix="/personas",
    tags=["Personas"],
)

ContextDependency = Annotated[
    RequestContext,
    Depends(get_request_context),
]

ControllerDependency = Annotated[
    PersonaController,
    Depends(get_persona_controller),
]


@router.get(
    "",
    response_model=PersonaListResponse,
    summary="List personas",
)
async def list_personas(
    context: ContextDependency,
    controller: ControllerDependency,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=200,
        ),
    ] = None,
    persona_status: Annotated[
        CatalogInstructionStatus | None,
        Query(
            alias="status",
            description="Filter by user enablement state.",
        ),
    ] = None,
    category: Annotated[
        list[CatalogInstructionCategory] | None,
        Query(description="Filter by one or more business categories."),
    ] = None,
    sort: Annotated[
        CatalogInstructionSort | None,
        Query(
            description=(
                "Order the filtered persona catalog. Date sorts use "
                "created_at."
            )
        ),
    ] = None,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Number of filtered personas to skip. Page size is 12.",
        ),
    ] = 0,
) -> PersonaListResponse:
    """List persona metadata without returning full instructions."""

    return await controller.list(
        user_id=context.user_id,
        search=search,
        status=persona_status,
        categories=category or (),
        sort=sort,
        offset=offset,
    )


@router.get(
    "/{persona_id}",
    response_model=PersonaResponse,
    summary="Get persona",
)
async def get_persona(
    context: ContextDependency,
    controller: ControllerDependency,
    persona_id: Annotated[
        str,
        Path(min_length=1),
    ],
) -> PersonaResponse:
    """Return a persona including its complete instructions."""

    return await controller.describe(
        user_id=context.user_id,
        persona_id=persona_id,
    )


@router.post(
    "",
    response_model=PersonaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create persona",
)
async def create_persona(
    payload: PersonaCreateRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> PersonaResponse:
    """Create a persona owned by the authenticated user."""

    return await controller.create(
        user_id=context.user_id,
        payload=payload,
    )


@router.patch(
    "/{persona_id}",
    response_model=PersonaResponse,
    summary="Modify persona",
)
async def patch_persona(
    payload: PersonaPatchRequest,
    context: ContextDependency,
    controller: ControllerDependency,
    persona_id: Annotated[
        str,
        Path(min_length=1),
    ],
) -> PersonaResponse:
    """Modify persona content or its user enabled state."""

    return await controller.patch(
        user_id=context.user_id,
        persona_id=persona_id,
        payload=payload,
    )


@router.delete(
    "/{persona_id}",
    response_model=DeleteResponse,
    summary="Delete persona",
)
async def delete_persona(
    context: ContextDependency,
    controller: ControllerDependency,
    persona_id: Annotated[
        str,
        Path(min_length=1),
    ],
) -> DeleteResponse:
    """Delete a persona when it has no blocking dependencies."""

    return await controller.delete(
        user_id=context.user_id,
        persona_id=persona_id,
    )
