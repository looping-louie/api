"""REST routes for pipeline definitions and changelog entries."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from src.app.controllers.pipeline import PipelineController
from src.app.schemas.shared import DeleteResponse
from src.app.schemas.pipeline import (
    PipelineChangelogListResponse,
    PipelineCreateRequest,
    PipelineListResponse,
    PipelinePatchRequest,
    PipelineResponse,
    PipelineStatusValue,
)

from .dependencies import (
    RequestContext,
    get_pipeline_controller,
    get_request_context,
)


router = APIRouter(prefix="/pipelines", tags=["Pipelines"])
ContextDependency = Annotated[
    RequestContext,
    Depends(get_request_context),
]
ControllerDependency = Annotated[
    PipelineController,
    Depends(get_pipeline_controller),
]
OffsetQuery = Annotated[
    int,
    Query(ge=0, description="Number of records to skip."),
]
StatusQuery = Annotated[
    PipelineStatusValue | None,
    Query(
        alias="status",
        description="Persisted status to include.",
    ),
]
SearchQuery = Annotated[
    str | None,
    Query(
        min_length=1,
        max_length=200,
        description="Case-insensitive name and description search.",
    ),
]
PipelineIdPath = Annotated[str, Path(min_length=1)]


@router.get(
    "",
    response_model=PipelineListResponse,
    summary="List pipelines",
)
async def list_pipelines(
    context: ContextDependency,
    controller: ControllerDependency,
    offset: OffsetQuery = 0,
    status_filter: StatusQuery = None,
    search: SearchQuery = None,
) -> PipelineListResponse:
    """Return ten filtered pipelines after the requested offset."""

    return await controller.list(
        user_id=context.user_id,
        offset=offset,
        status=status_filter,
        search=search,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "",
    response_model=PipelineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create pipeline",
)
async def create_pipeline(
    payload: PipelineCreateRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> PipelineResponse:
    """Create an enabled pipeline."""

    return await controller.create(
        user_id=context.user_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.get(
    "/{pipeline_id}",
    response_model=PipelineResponse,
    summary="Describe pipeline",
)
async def get_pipeline(
    context: ContextDependency,
    controller: ControllerDependency,
    pipeline_id: PipelineIdPath,
) -> PipelineResponse:
    """Return one complete pipeline with its Activity definitions."""

    return await controller.get(
        user_id=context.user_id,
        pipeline_id=pipeline_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.patch(
    "/{pipeline_id}",
    response_model=PipelineResponse,
    summary="Update pipeline",
)
async def patch_pipeline(
    payload: PipelinePatchRequest,
    context: ContextDependency,
    controller: ControllerDependency,
    pipeline_id: PipelineIdPath,
) -> PipelineResponse:
    """Update supplied mutable pipeline fields and resolve Activities."""

    return await controller.patch(
        user_id=context.user_id,
        pipeline_id=pipeline_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.delete(
    "/{pipeline_id}",
    response_model=DeleteResponse,
    summary="Delete pipeline",
)
async def delete_pipeline(
    context: ContextDependency,
    controller: ControllerDependency,
    pipeline_id: PipelineIdPath,
) -> DeleteResponse:
    """Archive one pipeline."""

    return await controller.delete(
        user_id=context.user_id,
        pipeline_id=pipeline_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.get(
    "/{pipeline_id}/changelog",
    response_model=PipelineChangelogListResponse,
    summary="List pipeline changelog",
)
async def list_pipeline_changelog(
    context: ContextDependency,
    controller: ControllerDependency,
    pipeline_id: PipelineIdPath,
    offset: OffsetQuery = 0,
) -> PipelineChangelogListResponse:
    """Return ten newest changelog entries after the requested offset."""

    return await controller.list_changelog(
        user_id=context.user_id,
        pipeline_id=pipeline_id,
        offset=offset,
        requested_workspace_id=context.requested_workspace_id,
    )
