"""REST routes for skill resources."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from src.app.catalogs.library import (
    LibraryCategory,
    LibrarySort,
    LibraryStatus,
)
from src.app.controllers.skill import SkillController
from src.app.schemas.shared import DeleteResponse
from src.app.schemas.skill import (
    SkillCreateRequest,
    SkillListResponse,
    SkillPatchRequest,
    SkillResponse,
)

from .dependencies import (
    RequestContext,
    get_request_context,
    get_skill_controller,
)


router = APIRouter(
    prefix="/skills",
    tags=["Skills"],
)

ContextDependency = Annotated[
    RequestContext,
    Depends(get_request_context),
]

ControllerDependency = Annotated[
    SkillController,
    Depends(get_skill_controller),
]


@router.get(
    "",
    response_model=SkillListResponse,
    summary="List skills",
)
async def list_skills(
    context: ContextDependency,
    controller: ControllerDependency,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=200,
        ),
    ] = None,
    skill_status: Annotated[
        LibraryStatus | None,
        Query(
            alias="status",
            description="Filter by workspace enablement state.",
        ),
    ] = None,
    category: Annotated[
        list[LibraryCategory] | None,
        Query(
            description="Filter by one or more business categories.",
        ),
    ] = None,
    sort: Annotated[
        LibrarySort | None,
        Query(description="Order the filtered skill catalog."),
    ] = None,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Number of filtered skills to skip. Page size is 12.",
        ),
    ] = 0,
) -> SkillListResponse:
    """List skill metadata without returning full instructions."""

    return await controller.list(
        user_id=context.user_id,
        requested_workspace_id=context.requested_workspace_id,
        search=search,
        status=skill_status,
        categories=category or (),
        sort=sort,
        offset=offset,
    )


@router.get(
    "/{skill_id}",
    response_model=SkillResponse,
    summary="Get skill",
)
async def get_skill(
    context: ContextDependency,
    controller: ControllerDependency,
    skill_id: Annotated[
        str,
        Path(min_length=1),
    ],
) -> SkillResponse:
    """Return a skill including its complete instructions."""

    return await controller.describe(
        user_id=context.user_id,
        skill_id=skill_id,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.post(
    "",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create skill",
)
async def create_skill(
    payload: SkillCreateRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> SkillResponse:
    """Create a skill in the selected workspace."""

    return await controller.create(
        user_id=context.user_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.patch(
    "/{skill_id}",
    response_model=SkillResponse,
    summary="Modify skill",
)
async def patch_skill(
    payload: SkillPatchRequest,
    context: ContextDependency,
    controller: ControllerDependency,
    skill_id: Annotated[
        str,
        Path(min_length=1),
    ],
) -> SkillResponse:
    """Modify skill content or its workspace enabled state."""

    return await controller.patch(
        user_id=context.user_id,
        skill_id=skill_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.delete(
    "/{skill_id}",
    response_model=DeleteResponse,
    summary="Delete skill",
)
async def delete_skill(
    context: ContextDependency,
    controller: ControllerDependency,
    skill_id: Annotated[
        str,
        Path(min_length=1),
    ],
) -> DeleteResponse:
    """Delete a skill when it has no blocking dependencies."""

    return await controller.delete(
        user_id=context.user_id,
        skill_id=skill_id,
        requested_workspace_id=context.requested_workspace_id,
    )
