"""REST routes for current API user profiles."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from src.app.catalogs.models import ModelCapability, ModelLab, ModelSort, ModelStatus
from src.app.catalogs.providers import ProviderId
from src.app.controllers.users import UserController
from src.app.schemas.model import ModelListResponse, ModelResponse
from src.app.schemas.user import UserResponse, UserSettingsRequest

from .dependencies import (
    RequestContext,
    get_request_context,
    get_user_controller,
)


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


@router.get('/me/models', response_model=ModelListResponse, summary='List user models')
async def list_user_models(
    context: ContextDependency,
    controller: ControllerDependency,
    provider_id: Annotated[ProviderId | None, Query(description='Filter models by provider.')] = None,
    capability: Annotated[ModelCapability | None, Query(description='Filter models by capability.')] = None,
    model_status: Annotated[ModelStatus | None, Query(alias='status', description='Filter models by catalog status.')] = None,
    lab: Annotated[list[ModelLab] | None, Query(description='Filter by one or more typed lab slugs.')] = None,
    sort: Annotated[ModelSort | None, Query(description='Order the filtered model catalog.')] = None,
    offset: Annotated[int, Query(ge=0, description='Number of filtered models to skip. Page size is 24.')] = 0,
    available: Annotated[bool | None, Query(description='Filter by User availability.')] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=200, description='Search by name, vendor, family or tag.')] = None,
    include_deprecated: Annotated[bool, Query(description='Include deprecated entries when status is not supplied.')] = False,
) -> ModelListResponse:
    """List curated models and availability for the current User."""

    return await controller.list(
        user_id=context.user_id,
        provider_id=provider_id,
        capability=capability,
        model_status=model_status,
        labs=lab or (),
        sort=sort,
        offset=offset,
        available=available,
        search=search,
        include_deprecated=include_deprecated,
    )


@router.get('/me/models/{model_id}', response_model=ModelResponse, summary='Describe user model')
async def describe_user_model(
    model_id: Annotated[str, Path(min_length=1, description='Logical model identifier.')],
    context: ContextDependency,
    controller: ControllerDependency,
) -> ModelResponse:
    """Return one catalog model and its availability for the current User."""

    return await controller.describe(user_id=context.user_id, model_id=model_id)
