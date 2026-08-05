"""REST routes for loop definitions and changelog entries."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from src.app.controllers.loop import LoopController
from src.app.controllers.loop_run import LoopRunController
from src.app.schemas.shared import DeleteResponse
from src.app.schemas.loop import (
    LoopChangelogListResponse,
    LoopCreateRequest,
    LoopListResponse,
    LoopPatchRequest,
    LoopResponse,
)
from src.app.schemas.loop_run import (
    LoopRunCreateRequest,
    LoopRunContinueRequest,
    LoopRunListResponse,
    LoopRunResponse,
)

from .dependencies import (
    RequestContext,
    get_loop_controller,
    get_loop_run_controller,
    get_request_context,
)


router = APIRouter(prefix="/loops", tags=["Loops"])
ContextDependency = Annotated[
    RequestContext,
    Depends(get_request_context),
]
ControllerDependency = Annotated[
    LoopController,
    Depends(get_loop_controller),
]
RunControllerDependency = Annotated[
    LoopRunController,
    Depends(get_loop_run_controller),
]
OffsetQuery = Annotated[
    int,
    Query(ge=0, description="Number of records to skip."),
]
LoopIdPath = Annotated[str, Path(min_length=1)]


@router.get("", response_model=LoopListResponse, summary="List loops")
async def list_loops(
    context: ContextDependency,
    controller: ControllerDependency,
    offset: OffsetQuery = 0,
) -> LoopListResponse:
    """Return ten loops after the requested offset."""

    return await controller.list(
        user_id=context.user_id,
        offset=offset,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "",
    response_model=LoopResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create loop",
)
async def create_loop(
    payload: LoopCreateRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> LoopResponse:
    """Create an active loop."""

    return await controller.create(
        user_id=context.user_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.get(
    "/{loop_id}/runs",
    response_model=LoopRunListResponse,
    summary="List loop runs",
)
async def list_loop_runs(
    context: ContextDependency,
    controller: RunControllerDependency,
    loop_id: LoopIdPath,
    offset: OffsetQuery = 0,
) -> LoopRunListResponse:
    """Return ten newest runs created from the selected loop."""

    return await controller.list(
        user_id=context.user_id,
        loop_id=loop_id,
        offset=offset,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "/{loop_id}/runs",
    response_model=LoopRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create loop run",
)
async def create_loop_run(
    payload: LoopRunCreateRequest,
    context: ContextDependency,
    controller: RunControllerDependency,
    loop_id: LoopIdPath,
) -> LoopRunResponse:
    """Create a loop run awaiting a CLI repository snapshot."""

    return await controller.create(
        user_id=context.user_id,
        loop_id=loop_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.get(
    "/{loop_id}/runs/{run_id}",
    response_model=LoopRunResponse,
    summary="Get loop run",
)
async def get_loop_run(
    context: ContextDependency,
    controller: RunControllerDependency,
    loop_id: LoopIdPath,
    run_id: Annotated[str, Path(min_length=1)],
) -> LoopRunResponse:
    """Return one run beneath the loop that created it."""

    return await controller.get(
        user_id=context.user_id,
        loop_id=loop_id,
        run_id=run_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "/{loop_id}/runs/{run_id}/continue",
    response_model=LoopRunResponse,
    summary="Continue loop run",
)
async def continue_loop_run(
    payload: LoopRunContinueRequest,
    context: ContextDependency,
    controller: RunControllerDependency,
    loop_id: LoopIdPath,
    run_id: Annotated[str, Path(min_length=1)],
) -> LoopRunResponse:
    """Persist CLI repository context before API generation begins."""

    return await controller.continue_collect_snapshot(
        user_id=context.user_id,
        loop_id=loop_id,
        run_id=run_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.get(
    "/{loop_id}",
    response_model=LoopResponse,
    summary="Get loop",
)
async def get_loop(
    context: ContextDependency,
    controller: ControllerDependency,
    loop_id: LoopIdPath,
) -> LoopResponse:
    """Return one complete loop."""

    return await controller.get(
        user_id=context.user_id,
        loop_id=loop_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.patch(
    "/{loop_id}",
    response_model=LoopResponse,
    summary="Update loop",
)
async def patch_loop(
    payload: LoopPatchRequest,
    context: ContextDependency,
    controller: ControllerDependency,
    loop_id: LoopIdPath,
) -> LoopResponse:
    """Update supplied mutable loop fields."""

    return await controller.patch(
        user_id=context.user_id,
        loop_id=loop_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.delete(
    "/{loop_id}",
    response_model=DeleteResponse,
    summary="Delete loop",
)
async def delete_loop(
    context: ContextDependency,
    controller: ControllerDependency,
    loop_id: LoopIdPath,
) -> DeleteResponse:
    """Delete a loop while preserving its changelog."""

    return await controller.delete(
        user_id=context.user_id,
        loop_id=loop_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.get(
    "/{loop_id}/changelog",
    response_model=LoopChangelogListResponse,
    summary="List loop changelog",
)
async def list_loop_changelog(
    context: ContextDependency,
    controller: ControllerDependency,
    loop_id: LoopIdPath,
    offset: OffsetQuery = 0,
) -> LoopChangelogListResponse:
    """Return ten newest changelog entries after the requested offset."""

    return await controller.list_changelog(
        user_id=context.user_id,
        loop_id=loop_id,
        offset=offset,
        requested_workspace_id=context.requested_workspace_id,
    )
