"""Controller for deleting Linked Services."""

from src.app.services.linked_services import LinkedServiceService


class LinkedServiceDeleteController:
    """Delete Linked Services owned by the current User."""

    async def delete(self, *, user_id: str, service_id: str) -> None:
        """Delete one Linked Service owned by the current User."""

        await self._linked_service_service.delete(
            user_id=user_id,
            service_id=service_id,
        )

    _linked_service_service: LinkedServiceService
