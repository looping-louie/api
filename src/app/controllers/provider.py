"""Thin controller for model provider configuration."""

from src.app.schemas.common import DeleteResponse
from src.app.schemas.providers import (
    ProviderResponse,
    ProviderSetRequest,
    ProviderTestResponse,
)
from src.app.services.providers.provider_service import ProviderService


class ProviderController:
    """Transforms provider schemas and delegates business logic."""

    def __init__(
        self,
        *,
        provider_service: ProviderService,
    ) -> None:
        self._provider_service = provider_service

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
    ) -> list[ProviderResponse]:
        providers = await self._provider_service.list(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return [
            ProviderResponse.model_validate(provider)
            for provider in providers
        ]

    async def describe(
        self,
        *,
        user_id: str,
        provider_id: str,
        requested_workspace_id: str | None = None,
    ) -> ProviderResponse:
        provider = await self._provider_service.describe(
            user_id=user_id,
            provider_id=provider_id,
            requested_workspace_id=requested_workspace_id,
        )

        return ProviderResponse.model_validate(provider)

    async def configure(
        self,
        *,
        user_id: str,
        provider_id: str,
        payload: ProviderSetRequest,
        requested_workspace_id: str | None = None,
    ) -> ProviderResponse:
        provider = await self._provider_service.configure(
            user_id=user_id,
            provider_id=provider_id,
            api_key=payload.api_key,
            base_url=payload.base_url,
            requested_workspace_id=requested_workspace_id,
        )

        return ProviderResponse.model_validate(provider)

    async def enable(
        self,
        *,
        user_id: str,
        provider_id: str,
        requested_workspace_id: str | None = None,
    ) -> ProviderResponse:
        provider = await self._provider_service.enable(
            user_id=user_id,
            provider_id=provider_id,
            requested_workspace_id=requested_workspace_id,
        )

        return ProviderResponse.model_validate(provider)

    async def disable(
        self,
        *,
        user_id: str,
        provider_id: str,
        requested_workspace_id: str | None = None,
    ) -> ProviderResponse:
        provider = await self._provider_service.disable(
            user_id=user_id,
            provider_id=provider_id,
            requested_workspace_id=requested_workspace_id,
        )

        return ProviderResponse.model_validate(provider)

    async def test(
        self,
        *,
        user_id: str,
        provider_id: str,
        requested_workspace_id: str | None = None,
    ) -> ProviderTestResponse:
        result = await self._provider_service.test(
            user_id=user_id,
            provider_id=provider_id,
            requested_workspace_id=requested_workspace_id,
        )

        return ProviderTestResponse.model_validate(result)

    async def delete(
        self,
        *,
        user_id: str,
        provider_id: str,
        requested_workspace_id: str | None = None,
    ) -> DeleteResponse:
        await self._provider_service.delete(
            user_id=user_id,
            provider_id=provider_id,
            requested_workspace_id=requested_workspace_id,
        )

        return DeleteResponse()
