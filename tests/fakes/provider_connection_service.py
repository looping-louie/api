"""Fake provider connectivity service."""

from src.app.catalogs.providers import ProviderId


class FakeProviderConnectionService:
    """Records provider connection attempts without making HTTP calls."""

    def __init__(self) -> None:
        self.calls: list[
            tuple[ProviderId, str | None, str | None]
        ] = []
        self.error: Exception | None = None

    async def test_connection(
        self,
        provider: ProviderId,
        api_key: str | None,
        base_url: str | None,
    ) -> None:
        """Record the connection attempt and optionally fail."""

        self.calls.append(
            (
                provider,
                api_key,
                base_url,
            )
        )

        if self.error is not None:
            raise self.error
