"""Thin controller for model provider configuration."""

from src.app.schemas.common import DeleteResponse
from src.app.schemas.providers import ProviderPatchRequest, ProviderResponse
from src.app.services.providers.provider_service import ProviderService


class ProviderController:
    """Transform provider schemas and delegate business logic."""

    def __init__(self, *, provider_service: ProviderService) -> None:
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
        return [
            ProviderResponse.model_validate(provider)
            for provider in providers
        ]

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
