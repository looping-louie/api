"""Controller for creating Linked Services."""

from src.app.schemas.linked_service import (
    LinkedServiceCreateRequest,
    LinkedServiceResponse,
)
from src.app.services.linked_services import LinkedServiceService

from .response import linked_service_response


class LinkedServiceCreateController:
    """Create Linked Services for the current User."""

    async def create(
        self,
        *,
        user_id: str,
        payload: LinkedServiceCreateRequest,
    ) -> LinkedServiceResponse:
        """Create one Linked Service for the current User."""

        linked_service = await self._linked_service_service.create(
            user_id=user_id,
            name=payload.name,
            provider_type=payload.provider_type.value,
            api_key=payload.config.api_key,
            base_url=payload.config.base_url,
            enabled=payload.enabled,
        )
        return linked_service_response(
            linked_service,
            service=self._linked_service_service,
        )

    _linked_service_service: LinkedServiceService