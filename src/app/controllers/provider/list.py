"""Controller for listing model providers."""

from __future__ import annotations

from src.app.schemas.providers import ProviderResponse
from src.app.services.providers.service import ProviderService


class ProviderListController:
    """List providers visible in a workspace."""

    def __init__(self, *, provider_service: ProviderService) -> None:
        """Store the provider application service."""
        self._provider_service = provider_service

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
    ) -> list[ProviderResponse]:
        """List providers visible in the selected workspace."""
        providers = await self._provider_service.list(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        return [ProviderResponse.model_validate(item) for item in providers]
