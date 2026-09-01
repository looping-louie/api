"""REST route for Project-scoped Pipeline-run discovery."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.app.controllers.pipelines import PipelineController
from src.app.schemas.pipeline import (
    PipelineRunListResponse,
    PipelineRunStatusValue,
)

from .dependencies import (
    RequestContext,
    get_pipeline_controller,
    get_request_context,
)


router = APIRouter(prefix='/pipeline-runs', tags=['Pipeline Runs'])
ContextDependency = Annotated[RequestContext, Depends(get_request_context)]
ControllerDependency = Annotated[
    PipelineController,
    Depends(get_pipeline_controller),
]


@router.get('', response_model=PipelineRunListResponse, summary='List pipeline runs')
async def list_pipeline_runs(
    context: ContextDependency,
    controller: ControllerDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    pipeline_id: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[
        PipelineRunStatusValue | None,
        Query(alias='status'),
    ] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
) -> PipelineRunListResponse:
    """Return filtered run history from the selected Project."""

    return await controller.list_runs(
        user_id=context.user_id,
        offset=offset,
        pipeline_id=pipeline_id,
        status=status_filter,
        created_from=created_from,
        created_to=created_to,
        requested_project_id=context.requested_project_id,
    )
