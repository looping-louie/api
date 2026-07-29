"""Controller for patching model provider configuration."""

from __future__ import annotations

from src.app.schemas.providers import ProviderPatchRequest, ProviderResponse
from src.app.services.providers.provider_service import ProviderService


class ProviderPatchController:
    """Patch one provider configuration."""

    def __init__(self, *, provider_service: ProviderService) -> None:
        """Store the provider application service."""
        self._provider_service = provider_service

    async def patch(
        self,
        *,
        user_id: str,
        provider_id: str,
        payload: ProviderPatchRequest,
        requested_workspace_id: str | None = None,
    ) -> ProviderResponse:
        """Patch one provider configuration."""
        supplied_fields = payload.model_fields_set
        provider = await self._provider_service.patch(
            user_id=user_id,
            provider_id=provider_id,
            api_key=payload.api_key,
            api_key_supplied="api_key" in supplied_fields,
            base_url=payload.base_url,
            base_url_supplied="base_url" in supplied_fields,
            enabled=payload.enabled,
            requested_workspace_id=requested_workspace_id,
        )
        return ProviderResponse.model_validate(provider)
