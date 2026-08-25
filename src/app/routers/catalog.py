"""REST routes for application-owned static catalogs."""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.app.controllers.catalog import CatalogController
from src.app.schemas.catalog import (
    CatalogModelListResponse,
    CatalogPersonaResponse,
    CatalogProviderResponse,
    CatalogSkillResponse,
)

from .dependencies import (
    RequestContext,
    get_catalog_controller,
    get_request_context,
)


router = APIRouter(prefix='/catalog', tags=['Catalog'])

ContextDependency = Annotated[RequestContext, Depends(get_request_context)]
ControllerDependency = Annotated[
    CatalogController,
    Depends(get_catalog_controller),
]


@router.get(
    '/models',
    response_model=CatalogModelListResponse,
    summary='List model catalog',
)
async def list_models(
    _: ContextDependency,
    controller: ControllerDependency,
) -> CatalogModelListResponse:
    """List static logical model definitions without workspace state."""

    return controller.list_models()


@router.get(
    '/providers',
    response_model=list[CatalogProviderResponse],
    summary='List provider catalog',
)
async def list_providers(
    _: ContextDependency,
    controller: ControllerDependency,
) -> list[CatalogProviderResponse]:
    """List static provider definitions without workspace state."""

    return controller.list_providers()


@router.get(
    '/personas',
    response_model=list[CatalogPersonaResponse],
    summary='List built-in Persona catalog',
)
async def list_personas(
    _: ContextDependency,
    controller: ControllerDependency,
) -> list[CatalogPersonaResponse]:
    """List built-in Persona definitions without workspace state."""

    return controller.list_personas()


@router.get(
    '/skills',
    response_model=list[CatalogSkillResponse],
    summary='List built-in Skill catalog',
)
async def list_skills(
    _: ContextDependency,
    controller: ControllerDependency,
) -> list[CatalogSkillResponse]:
    """List built-in Skill definitions without workspace state."""

    return controller.list_skills()
