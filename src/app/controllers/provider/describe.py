"""Controller for describing one model provider."""

from __future__ import annotations

from src.app.schemas.provider import ProviderResponse
from src.app.services.providers.service import ProviderService


class ProviderDescribeController:
    """Return one provider and its workspace state."""

    def __init__(self, *, provider_service: ProviderService) -> None:
        """Store the provider application service."""
        self._provider_service = provider_service

    async def get(
        self,
        *,
        user_id: str,
        provider_id: str,
        requested_workspace_id: str | None = None,
    ) -> ProviderResponse:
        """Get one catalog provider and its workspace state."""
        provider = await self._provider_service.get(
            user_id=user_id,
            provider_id=provider_id,
            requested_workspace_id=requested_workspace_id,
        )
        return ProviderResponse.model_validate(provider)
