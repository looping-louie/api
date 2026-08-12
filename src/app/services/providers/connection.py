"""Connectivity checks for configured model providers."""

from typing import Protocol

import httpx

from src.app.catalogs.providers import ProviderId


class ProviderConnectionError(RuntimeError):
    """Raised when a provider configuration cannot be reached or authorised."""


class ProviderConnectionService(Protocol):
    """Tests provider credentials without exposing them."""

    async def test_connection(
        self,
        provider: ProviderId,
        api_key: str | None,
        base_url: str | None,
    ) -> None:
        """Raise ProviderConnectionError when the connection is unusable."""


class HttpProviderConnectionService:
    """HTTP implementation using each provider's model-list endpoint."""

    _PATHS = {
        ProviderId.ANTHROPIC: "/models",
        ProviderId.NVIDIA: "/models",
        ProviderId.OLLAMA: "/api/tags",
        ProviderId.OPENAI: "/models",
        ProviderId.TOGETHER: "/models",
    }

    def __init__(self, timeout_seconds: float = 15.0) -> None:
        """Configure the provider-test timeout."""

        self._timeout = httpx.Timeout(timeout_seconds)

    async def test_connection(
        self,
        provider: ProviderId,
        api_key: str | None,
        base_url: str | None,
    ) -> None:
        """Call a harmless model-list endpoint."""

        if not base_url:
            raise ProviderConnectionError(
                f"Provider '{provider}' has no base URL."
            )

        path = self._PATHS.get(provider)

        if path is None:
            raise ProviderConnectionError(
                f"Provider '{provider}' cannot be tested."
            )

        headers = self._build_headers(
            provider=provider,
            api_key=api_key,
        )
        url = f"{base_url.rstrip('/')}{path}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderConnectionError(
                f"Provider '{provider}' returned HTTP "
                f"{exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderConnectionError(
                f"Provider '{provider}' could not be reached."
            ) from exc

    @staticmethod
    def _build_headers(
        provider: ProviderId,
        api_key: str | None,
    ) -> dict[str, str]:
        """Build authentication headers without logging their values."""

        if not api_key:
            return {}

        if provider == ProviderId.ANTHROPIC:
            return {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }

        return {
            "Authorization": f"Bearer {api_key}",
        }
