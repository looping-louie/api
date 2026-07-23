"""Test double for provider model counts."""

from src.app.catalogs.providers import ProviderId


class FakeModelRegistryService:
    """Return deterministic provider counts in focused service tests."""

    def __init__(
        self,
        counts: dict[ProviderId, int] | None = None,
    ) -> None:
        self._counts = {
            provider: max(0, count)
            for provider, count in (counts or {}).items()
        }

    def count_by_provider(self, provider: ProviderId) -> int:
        """Return the configured count or zero."""

        return self._counts.get(provider, 0)
