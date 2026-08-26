"""REST routes for current API user profiles."""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.app.controllers.user import UserController
from src.app.schemas.user import UserResponse

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


@router.put('/me', response_model=UserResponse, summary='Register current user')
async def register_current_user(
    context: ContextDependency,
    controller: ControllerDependency,
) -> UserResponse:
    """Register the identity supplied with this request when it is new."""

    return await controller.register_current(user_id=context.user_id)