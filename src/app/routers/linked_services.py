"""REST routes for workspace-owned linked services."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from src.app.controllers.linked_services import LinkedServiceController
from src.app.schemas.linked_service import (
    LinkedServiceCreateRequest,
    LinkedServicePatchRequest,
    LinkedServiceResponse,
)
from src.app.schemas.shared import DeleteResponse

from .dependencies import RequestContext, get_linked_service_controller, get_request_context


router = APIRouter(prefix='/linked-services', tags=['Linked Services'])
ContextDependency = Annotated[RequestContext, Depends(get_request_context)]
ControllerDependency = Annotated[LinkedServiceController, Depends(get_linked_service_controller)]
ServiceIdPath = Annotated[str, Path(min_length=1, description='Linked service identifier.')]


@router.get('', response_model=list[LinkedServiceResponse], summary='List linked services')
async def list_linked_services(context: ContextDependency, controller: ControllerDependency) -> list[LinkedServiceResponse]:
    """List linked services in the selected workspace."""
    return await controller.list(user_id=context.user_id, requested_workspace_id=context.requested_workspace_id)


@router.post('', response_model=LinkedServiceResponse, status_code=status.HTTP_201_CREATED, summary='Create linked service')
async def create_linked_service(payload: LinkedServiceCreateRequest, context: ContextDependency, controller: ControllerDependency) -> LinkedServiceResponse:
    """Create a linked service after validating its candidate configuration."""
    return await controller.create(user_id=context.user_id, payload=payload, requested_workspace_id=context.requested_workspace_id)


@router.get('/{service_id}', response_model=LinkedServiceResponse, summary='Get linked service')
async def get_linked_service(service_id: ServiceIdPath, context: ContextDependency, controller: ControllerDependency) -> LinkedServiceResponse:
    """Return one linked service from the selected workspace."""
    return await controller.get(user_id=context.user_id, service_id=service_id, requested_workspace_id=context.requested_workspace_id)


@router.patch('/{service_id}', response_model=LinkedServiceResponse, summary='Update linked service')
async def patch_linked_service(service_id: ServiceIdPath, payload: LinkedServicePatchRequest, context: ContextDependency, controller: ControllerDependency) -> LinkedServiceResponse:
    """Update mutable linked-service fields."""
    return await controller.patch(user_id=context.user_id, service_id=service_id, payload=payload, requested_workspace_id=context.requested_workspace_id)


@router.delete('/{service_id}', response_model=DeleteResponse, summary='Delete linked service')
async def delete_linked_service(service_id: ServiceIdPath, context: ContextDependency, controller: ControllerDependency) -> DeleteResponse:
    """Delete one linked service from the selected workspace."""
    await controller.delete(user_id=context.user_id, service_id=service_id, requested_workspace_id=context.requested_workspace_id)
    return DeleteResponse()
