"""REST routes for pipeline definitions and changelog entries."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, Path, Query, status

from src.app.controllers.pipeline import PipelineController
from src.app.schemas.shared import DeleteResponse
from src.app.schemas.pipeline import (
    PipelineChangelogListResponse,
    PipelineRunClaimRequest,
    PipelineRunClaimResponse,
    PipelineRunClaimableListResponse,
    PipelineRunContinueRequest,
    PipelineRunEventListResponse,
    PipelineCreateRequest,
    PipelineListResponse,
    PipelinePatchRequest,
    PipelineRunCreateRequest,
    PipelineRunLeaseRenewRequest,
    PipelineRunLeaseResponse,
    PipelineRunResponse,
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


@router.post(
    '/{pipeline_id}/runs',
    response_model=PipelineRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Create pipeline run',
)
async def create_pipeline_run(
    payload: PipelineRunCreateRequest,
    context: ContextDependency,
    controller: ControllerDependency,
    pipeline_id: PipelineIdPath,
) -> PipelineRunResponse:
    """Create one dependency-aware pipeline execution."""

    return await controller.create_run(
        user_id=context.user_id, pipeline_id=pipeline_id, payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.get(
    '/{pipeline_id}/runs',
    response_model=PipelineRunClaimableListResponse,
    summary='List claimable pipeline runs',
)
async def list_claimable_pipeline_runs(
    context: ContextDependency,
    controller: ControllerDependency,
    pipeline_id: PipelineIdPath,
    claimable: Annotated[bool, Query()],
) -> PipelineRunClaimableListResponse:
    """Return candidates for the explicit runtime claimable filter."""

    if not claimable:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='claimable must be true.',
        )
    return await controller.list_claimable_runs(
        user_id=context.user_id, pipeline_id=pipeline_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    '/{pipeline_id}/runs/{run_id}/start',
    response_model=PipelineRunResponse,
    summary='Start pipeline run',
)
async def start_pipeline_run(
    context: ContextDependency,
    controller: ControllerDependency,
    pipeline_id: PipelineIdPath,
    run_id: Annotated[str, Path(min_length=1)],
) -> PipelineRunResponse:
    """Make one prepared Pipeline run eligible for its assigned executor."""

    return await controller.start_run(
        user_id=context.user_id,
        pipeline_id=pipeline_id,
        run_id=run_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.patch(
    '/{pipeline_id}/runs/{run_id}',
    response_model=PipelineRunClaimResponse,
    summary='Claim pipeline run',
)
async def claim_pipeline_run(
    payload: PipelineRunClaimRequest,
    context: ContextDependency,
    controller: ControllerDependency,
    pipeline_id: PipelineIdPath,
    run_id: Annotated[str, Path(min_length=1)],
    if_match: Annotated[str, Header(alias='If-Match', min_length=1)],
) -> PipelineRunClaimResponse:
    """Claim one current pipeline run using the entity tag from its listing."""

    return await controller.claim_run(
        user_id=context.user_id, pipeline_id=pipeline_id, run_id=run_id,
        payload=payload, if_match=if_match,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.get(
    '/{pipeline_id}/runs/{run_id}',
    response_model=PipelineRunResponse,
    summary='Get pipeline run',
)
async def get_pipeline_run(
    context: ContextDependency,
    controller: ControllerDependency,
    pipeline_id: PipelineIdPath,
    run_id: Annotated[str, Path(min_length=1)],
) -> PipelineRunResponse:
    """Return a pipeline execution and its selected child run."""

    return await controller.get_run(
        user_id=context.user_id, pipeline_id=pipeline_id, run_id=run_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.get(
    '/{pipeline_id}/runs/{run_id}/events',
    response_model=PipelineRunEventListResponse,
    summary='List pipeline run events',
)
async def list_pipeline_run_events(
    context: ContextDependency,
    controller: ControllerDependency,
    pipeline_id: PipelineIdPath,
    run_id: Annotated[str, Path(min_length=1)],
) -> PipelineRunEventListResponse:
    """Return the append-only execution ledger for one Pipeline run."""

    return await controller.list_events(
        user_id=context.user_id, pipeline_id=pipeline_id, run_id=run_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    '/{pipeline_id}/runs/{run_id}/lease',
    response_model=PipelineRunLeaseResponse,
    summary='Renew pipeline run lease',
)
async def renew_pipeline_run_lease(
    payload: PipelineRunLeaseRenewRequest,
    context: ContextDependency,
    controller: ControllerDependency,
    pipeline_id: PipelineIdPath,
    run_id: Annotated[str, Path(min_length=1)],
) -> PipelineRunLeaseResponse:
    """Extend an active worker lease before continuing runtime execution."""

    return await controller.renew_lease(
        user_id=context.user_id, pipeline_id=pipeline_id, run_id=run_id,
        lease_token=payload.lease_token,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    '/{pipeline_id}/runs/{run_id}/continue',
    response_model=PipelineRunResponse,
    summary='Continue pipeline run',
)
async def continue_pipeline_run(
    payload: PipelineRunContinueRequest,
    context: ContextDependency,
    controller: ControllerDependency,
    pipeline_id: PipelineIdPath,
    run_id: Annotated[str, Path(min_length=1)],
) -> PipelineRunResponse:
    """Schedule after the selected child run reaches a terminal state."""

    return await controller.continue_run(
        user_id=context.user_id, pipeline_id=pipeline_id, run_id=run_id,
        payload=payload,
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
