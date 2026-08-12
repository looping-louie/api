"""REST routes for activity definitions and their changelog entries."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from src.app.controllers.activity import ActivityController
from src.app.schemas.activity import ActivityChangelogListResponse, ActivityCreateRequest, ActivityListResponse, ActivityPatchRequest, ActivityResponse
from src.app.schemas.shared import DeleteResponse

from .dependencies import RequestContext, get_activity_controller, get_request_context


router = APIRouter(prefix='/activities', tags=['Activities'])
ContextDependency = Annotated[RequestContext, Depends(get_request_context)]
ControllerDependency = Annotated[ActivityController, Depends(get_activity_controller)]
OffsetQuery = Annotated[int, Query(ge=0, description='Number of records to skip.')]
ActivityIdPath = Annotated[str, Path(min_length=1)]


@router.get('', response_model=ActivityListResponse, summary='List activities')
async def list_activities(context: ContextDependency, controller: ControllerDependency, offset: OffsetQuery = 0) -> ActivityListResponse:
    """Return ten activities after the requested offset."""

    return await controller.list(user_id=context.user_id, offset=offset, requested_workspace_id=context.requested_workspace_id)


@router.post('', response_model=ActivityResponse, status_code=status.HTTP_201_CREATED, summary='Create activity')
async def create_activity(payload: ActivityCreateRequest, context: ContextDependency, controller: ControllerDependency) -> ActivityResponse:
    """Create an active activity."""

    return await controller.create(user_id=context.user_id, payload=payload, requested_workspace_id=context.requested_workspace_id)


@router.get('/{activity_id}', response_model=ActivityResponse, summary='Get activity')
async def get_activity(context: ContextDependency, controller: ControllerDependency, activity_id: ActivityIdPath) -> ActivityResponse:
    """Return one complete activity."""

    return await controller.get(user_id=context.user_id, activity_id=activity_id, requested_workspace_id=context.requested_workspace_id)


@router.patch('/{activity_id}', response_model=ActivityResponse, summary='Update activity')
async def patch_activity(payload: ActivityPatchRequest, context: ContextDependency, controller: ControllerDependency, activity_id: ActivityIdPath) -> ActivityResponse:
    """Update supplied mutable activity fields."""

    return await controller.patch(user_id=context.user_id, activity_id=activity_id, payload=payload, requested_workspace_id=context.requested_workspace_id)


@router.delete('/{activity_id}', response_model=DeleteResponse, summary='Delete activity')
async def delete_activity(context: ContextDependency, controller: ControllerDependency, activity_id: ActivityIdPath) -> DeleteResponse:
    """Delete an activity while preserving its changelog."""

    return await controller.delete(user_id=context.user_id, activity_id=activity_id, requested_workspace_id=context.requested_workspace_id)


@router.get('/{activity_id}/changelog', response_model=ActivityChangelogListResponse, summary='List activity changelog')
async def list_activity_changelog(context: ContextDependency, controller: ControllerDependency, activity_id: ActivityIdPath, offset: OffsetQuery = 0) -> ActivityChangelogListResponse:
    """Return ten newest activity changelog entries after the requested offset."""

    return await controller.list_changelog(user_id=context.user_id, activity_id=activity_id, offset=offset, requested_workspace_id=context.requested_workspace_id)