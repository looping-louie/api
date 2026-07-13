from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from src.app.controllers.loop import LoopController
from src.app.schemas.common import DeleteResponse
from src.app.schemas.loop import (
    LoopCreateRequest,
    LoopListResponse,
    LoopResponse,
    LoopUpdateRequest,
    LoopValidationResponse,
)

from .dependencies import (
    RequestContext,
    get_loop_controller,
    get_request_context,
)


router = APIRouter(
    prefix="/loops",
    tags=["Loops"],
)

ContextDependency = Annotated[
    RequestContext,
    Depends(get_request_context),
]

ControllerDependency = Annotated[
    LoopController,
    Depends(get_loop_controller),
]


@router.get(
    "/list",
    response_model=LoopListResponse,
    summary="List loops",
)
async def list_loops(
    context: ContextDependency,
    controller: ControllerDependency,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=200,
        ),
    ] = None,
) -> LoopListResponse:
    """List loop metadata and configuration summaries."""

    return await controller.list(
        user_id=context.user_id,
        requested_workspace_id=context.requested_workspace_id,
        search=search,
    )


@router.get(
    "/describe/{loop_id}",
    response_model=LoopResponse,
    summary="Describe loop",
)
async def describe_loop(
    context: ContextDependency,
    controller: ControllerDependency,
    loop_id: Annotated[
        str,
        Path(min_length=1),
    ],
) -> LoopResponse:
    """Return a loop including council, models and iteration limit."""

    return await controller.describe(
        user_id=context.user_id,
        loop_id=loop_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "/create",
    response_model=LoopResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create loop",
)
async def create_loop(
    payload: LoopCreateRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> LoopResponse:
    """Create a loop in the selected workspace."""

    return await controller.create(
        user_id=context.user_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "/update/{loop_id}",
    response_model=LoopResponse,
    summary="Update loop",
)
async def update_loop(
    payload: LoopUpdateRequest,
    context: ContextDependency,
    controller: ControllerDependency,
    loop_id: Annotated[
        str,
        Path(min_length=1),
    ],
) -> LoopResponse:
    """Update a loop configuration."""

    return await controller.update(
        user_id=context.user_id,
        loop_id=loop_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.delete(
    "/delete/{loop_id}",
    response_model=DeleteResponse,
    summary="Delete loop",
)
async def delete_loop(
    context: ContextDependency,
    controller: ControllerDependency,
    loop_id: Annotated[
        str,
        Path(min_length=1),
    ],
) -> DeleteResponse:
    """Delete a loop without deleting historical run snapshots."""

    return await controller.delete(
        user_id=context.user_id,
        loop_id=loop_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "/validate/{loop_id}",
    response_model=LoopValidationResponse,
    summary="Validate loop",
)
async def validate_loop(
    context: ContextDependency,
    controller: ControllerDependency,
    loop_id: Annotated[
        str,
        Path(min_length=1),
    ],
) -> LoopValidationResponse:
    """Validate council roles and model references for a stored loop."""

    return await controller.validate(
        user_id=context.user_id,
        loop_id=loop_id,
        requested_workspace_id=context.requested_workspace_id,
    )
