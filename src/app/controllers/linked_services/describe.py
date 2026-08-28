"""Controller for describing Linked Services."""

from src.app.schemas.linked_service import LinkedServiceResponse
from src.app.services.linked_services import LinkedServiceService

from .response import linked_service_response


class LinkedServiceDescribeController:
    """Retrieve one Linked Service owned by the current User."""

    async def get(
        self,
        *,
        user_id: str,
        service_id: str,
    ) -> LinkedServiceResponse:
        """Get one Linked Service owned by the current User."""

        linked_service = await self._linked_service_service.get(
            user_id=user_id,
            service_id=service_id,
        )
        return linked_service_response(
            linked_service,
            service=self._linked_service_service,
        )

    _linked_service_service: LinkedServiceService
