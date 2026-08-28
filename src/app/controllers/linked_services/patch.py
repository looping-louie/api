"""Controller for updating Linked Services."""

from src.app.schemas.linked_service import (
    LinkedServicePatchRequest,
    LinkedServiceResponse,
)
from src.app.services.linked_services import LinkedServiceService

from .response import linked_service_response


class LinkedServicePatchController:
    """Update mutable fields on Linked Services."""

    async def patch(
        self,
        *,
        user_id: str,
        service_id: str,
        payload: LinkedServicePatchRequest,
    ) -> LinkedServiceResponse:
        """Patch mutable fields of one Linked Service."""

        config = payload.config
        supplied_config_fields = config.model_fields_set if config is not None else set()
        linked_service = await self._linked_service_service.patch(
            user_id=user_id,
            service_id=service_id,
            name=payload.name,
            api_key=config.api_key if config is not None else None,
            api_key_supplied='api_key' in supplied_config_fields,
            base_url=config.base_url if config is not None else None,
            base_url_supplied='base_url' in supplied_config_fields,
            enabled=payload.enabled,
        )
        return linked_service_response(
            linked_service,
            service=self._linked_service_service,
        )

    _linked_service_service: LinkedServiceService