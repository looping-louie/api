"""REST routes for current API user profiles."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.app.controllers.user import UserController
from src.app.schemas.user import UserResponse, UserSettingsRequest

from .dependencies import RequestContext, get_request_context, get_user_controller


router = APIRouter(prefix='/users', tags=['Users'])
ContextDependency = Annotated[RequestContext, Depends(get_request_context)]
ControllerDependency = Annotated[UserController, Depends(get_user_controller)]


@router.get('/me', response_model=UserResponse, summary='Get current user')
async def get_current_user(
    context: ContextDependency,
    controller: ControllerDependency,
) -> UserResponse:
    """Return the profile for the identity supplied with this request."""

    return await controller.get_current(user_id=context.user_id)


@router.post(
    '',
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Register current user',
)
async def register_current_user(
    context: ContextDependency,
    controller: ControllerDependency,
) -> UserResponse:
    """Register the identity supplied with this request when it is new."""

    return await controller.register_current(user_id=context.user_id)


@router.patch('/me', response_model=UserResponse, summary='Update current user settings')
async def update_current_user_settings(
    settings: UserSettingsRequest,
    context: ContextDependency,
    controller: ControllerDependency,
) -> UserResponse:
    """Replace settings for the identity supplied with this request."""

    return await controller.update_current_settings(
        user_id=context.user_id,
        settings=settings,
    )
