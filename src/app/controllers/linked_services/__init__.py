"""Controllers for linked-service HTTP operations."""

from src.app.models.linked_service import LinkedService
from src.app.schemas.linked_service import (
    LinkedServiceCreateRequest,
    LinkedServicePatchRequest,
    LinkedServiceResponse,
)
from src.app.services.linked_services import LinkedServiceService


class LinkedServiceController:
    """Translate linked-service HTTP contracts to application operations."""

    def __init__(self, *, linked_service_service: LinkedServiceService) -> None:
        """Store the linked-service application service."""
        self._linked_service_service = linked_service_service

    async def list(self, *, user_id: str) -> list[LinkedServiceResponse]:
        """List linked services owned by the current user."""
        linked_services = await self._linked_service_service.list(user_id=user_id)
        return [self._response(linked_service) for linked_service in linked_services]

    async def get(self, *, user_id: str, service_id: str) -> LinkedServiceResponse:
        """Get one linked service owned by the current user."""
        linked_service = await self._linked_service_service.get(user_id=user_id, service_id=service_id)
        return self._response(linked_service)

    async def create(self, *, user_id: str, payload: LinkedServiceCreateRequest) -> LinkedServiceResponse:
        """Create one linked service for the current user."""
        linked_service = await self._linked_service_service.create(
            user_id=user_id, name=payload.name,
            provider_type=payload.provider_type.value,
            api_key=payload.config.api_key, base_url=payload.config.base_url,
            enabled=payload.enabled,
        )
        return self._response(linked_service)

    async def patch(self, *, user_id: str, service_id: str, payload: LinkedServicePatchRequest) -> LinkedServiceResponse:
        """Patch mutable fields of one linked service."""
        config = payload.config
        supplied_config_fields = config.model_fields_set if config is not None else set()
        linked_service = await self._linked_service_service.patch(
            user_id=user_id, service_id=service_id, name=payload.name,
            api_key=config.api_key if config is not None else None,
            api_key_supplied='api_key' in supplied_config_fields,
            base_url=config.base_url if config is not None else None,
            base_url_supplied='base_url' in supplied_config_fields,
            enabled=payload.enabled,
        )
        return self._response(linked_service)

    async def delete(self, *, user_id: str, service_id: str) -> None:
        """Delete one linked service owned by the current user."""
        await self._linked_service_service.delete(user_id=user_id, service_id=service_id)

    def _response(self, linked_service: LinkedService) -> LinkedServiceResponse:
        """Build a safe response with catalog-derived model availability."""
        return LinkedServiceResponse.model_validate({
            'id': linked_service.id,
            'name': linked_service.name,
            'provider_type': linked_service.provider_type,
            'enabled': linked_service.enabled,
            'config': {
                'base_url': linked_service.base_url,
                'key_trimmed': linked_service.key_trimmed,
                'configured': self._linked_service_service.is_configured(
                    linked_service,
                ),
                'available_models': self._linked_service_service.available_models(
                    linked_service.provider_type,
                ),
            },
            'version': linked_service.version,
            'created_at': linked_service.created_at,
            'updated_at': linked_service.updated_at,
        })
