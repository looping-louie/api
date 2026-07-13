from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from src.app.controllers.council import CouncilController
from src.app.schemas.common import DeleteResponse
from src.app.schemas.council import (
    CouncilCreateRequest,
    CouncilListResponse,
    CouncilResponse,
    CouncilUpdateRequest,
)

from .dependencies import (
    RequestContext,
    get_council_controller,
    get_request_context,
)


router = APIRouter(
    prefix="/councils",
    tags=["Councils"],
)

ContextDependency = Annotated[
    RequestContext,
    Depends(get_request_context),
]

ControllerDependency = Annotated[
    CouncilController,
    Depends(get_council_controller),
]


@router.get(
    "/list",
    response_model=CouncilListResponse,
    summary="List councils",
)
async def list_councils(
    context: ContextDependency,
    controller: ControllerDependency,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=200,
        ),
    ] = None,
) -> CouncilListResponse:
    """List council metadata without expanding assignments."""

    return await controller.list(
        user_id=context.user_id,
        requested_workspace_id=context.requested_workspace_id,
        search=search,
    )


@router.get(
    "/describe/{council_id}",
    response_model=CouncilResponse,
    summary="Describe council",
)
async def describe_council(
    context: ContextDependency,
    controller: ControllerDependency,
    council_id: Annotated[
        str,
        Path(min_length=1),
    ],
) -> CouncilResponse:
    """Return a council including assignments, personas and skills."""

    return await controller.describe(
        user_id=context.user_id,
        council_id=council_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "/create",
    response_model=CouncilResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create council",
)
async def create_council(
    payload: CouncilCreateRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> CouncilResponse:
    """Create a council in the selected workspace."""

    return await controller.create(
        user_id=context.user_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "/update/{council_id}",
    response_model=CouncilResponse,
    summary="Update council",
)
async def update_council(
    payload: CouncilUpdateRequest,
    context: ContextDependency,
    controller: ControllerDependency,
    council_id: Annotated[
        str,
        Path(min_length=1),
    ],
) -> CouncilResponse:
    """Update a council and optionally replace its assignments."""

    return await controller.update(
        user_id=context.user_id,
        council_id=council_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.delete(
    "/delete/{council_id}",
    response_model=DeleteResponse,
    summary="Delete council",
)
async def delete_council(
    context: ContextDependency,
    controller: ControllerDependency,
    council_id: Annotated[
        str,
        Path(min_length=1),
    ],
) -> DeleteResponse:
    """Delete a council when no loop depends on it."""

    return await controller.delete(
        user_id=context.user_id,
        council_id=council_id,
        requested_workspace_id=context.requested_workspace_id,
    )
