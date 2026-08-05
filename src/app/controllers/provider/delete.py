"""Controller for deleting model provider configuration."""

from __future__ import annotations

from src.app.schemas.shared import DeleteResponse
from src.app.services.providers.service import ProviderService


class ProviderDeleteController:
    """Delete one provider's workspace configuration."""

    def __init__(self, *, provider_service: ProviderService) -> None:
        """Store the provider application service."""
        self._provider_service = provider_service

    async def delete(
        self,
        *,
        user_id: str,
        provider_id: str,
        requested_workspace_id: str | None = None,
    ) -> DeleteResponse:
        """Delete one provider's workspace configuration."""
        await self._provider_service.delete(
            user_id=user_id,
            provider_id=provider_id,
            requested_workspace_id=requested_workspace_id,
        )
        return DeleteResponse()
