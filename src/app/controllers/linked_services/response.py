"""Linked Service HTTP response mapping."""

from src.app.models.linked_service import LinkedService
from src.app.schemas.linked_service import LinkedServiceResponse
from src.app.services.linked_services import LinkedServiceService


def linked_service_response(
    linked_service: LinkedService,
    *,
    service: LinkedServiceService,
) -> LinkedServiceResponse:
    """Build a safe response with catalog-derived model availability."""

    return LinkedServiceResponse.model_validate({
        'id': linked_service.id,
        'name': linked_service.name,
        'provider_type': linked_service.provider_type,
        'enabled': linked_service.enabled,
        'config': {
            'base_url': linked_service.base_url,
            'key_trimmed': linked_service.key_trimmed,
            'configured': service.is_configured(linked_service),
            'available_models': service.available_models(
                linked_service.provider_type,
            ),
        },
        'version': linked_service.version,
        'created_at': linked_service.created_at,
        'updated_at': linked_service.updated_at,
    })
