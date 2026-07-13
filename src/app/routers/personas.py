from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from src.app.controllers.persona import PersonaController
from src.app.schemas.common import DeleteResponse
from src.app.schemas.persona import (
    PersonaCreateRequest,
    PersonaListResponse,
    PersonaResponse,
    PersonaUpdateRequest,
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
    "/list",
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
) -> PersonaListResponse:
    """List persona metadata without returning full instructions."""

    return await controller.list(
        user_id=context.user_id,
        requested_workspace_id=context.requested_workspace_id,
        search=search,
    )


@router.get(
    "/describe/{persona_id}",
    response_model=PersonaResponse,
    summary="Describe persona",
)
async def describe_persona(
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
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "/create",
    response_model=PersonaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create persona",
)
async def create_persona(
    payload: PersonaCreateRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> PersonaResponse:
    """Create a persona in the selected workspace."""

    return await controller.create(
        user_id=context.user_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "/update/{persona_id}",
    response_model=PersonaResponse,
    summary="Update persona",
)
async def update_persona(
    payload: PersonaUpdateRequest,
    context: ContextDependency,
    controller: ControllerDependency,
    persona_id: Annotated[
        str,
        Path(min_length=1),
    ],
) -> PersonaResponse:
    """Update an existing persona."""

    return await controller.update(
        user_id=context.user_id,
        persona_id=persona_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.delete(
    "/delete/{persona_id}",
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
        requested_workspace_id=context.requested_workspace_id,
    )
