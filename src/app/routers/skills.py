from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from src.app.controllers.skill import SkillController
from src.app.schemas.common import DeleteResponse
from src.app.schemas.skill import (
    SkillCreateRequest,
    SkillListResponse,
    SkillResponse,
    SkillUpdateRequest,
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
    "/list",
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
) -> SkillListResponse:
    """List skill metadata without returning full instructions."""

    return await controller.list(
        user_id=context.user_id,
        requested_workspace_id=context.requested_workspace_id,
        search=search,
    )


@router.get(
    "/describe/{skill_id}",
    response_model=SkillResponse,
    summary="Describe skill",
)
async def describe_skill(
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
    "/create",
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


@router.post(
    "/update/{skill_id}",
    response_model=SkillResponse,
    summary="Update skill",
)
async def update_skill(
    payload: SkillUpdateRequest,
    context: ContextDependency,
    controller: ControllerDependency,
    skill_id: Annotated[
        str,
        Path(min_length=1),
    ],
) -> SkillResponse:
    """Update an existing skill."""

    return await controller.update(
        user_id=context.user_id,
        skill_id=skill_id,
        payload=payload,
        requested_workspace_id=context.requested_workspace_id,
    )


@router.delete(
    "/delete/{skill_id}",
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
