"""Controller for listing Linked Services."""

from src.app.schemas.linked_service import LinkedServiceResponse
from src.app.services.linked_services import LinkedServiceService

from .response import linked_service_response


class LinkedServiceListController:
    """List Linked Services owned by the current User."""

    async def list(self, *, user_id: str) -> list[LinkedServiceResponse]:
        """List Linked Services owned by the current User."""

        linked_services = await self._linked_service_service.list(user_id=user_id)
        return [
            linked_service_response(
                linked_service,
                service=self._linked_service_service,
            )
            for linked_service in linked_services
        ]

    _linked_service_service: LinkedServiceService