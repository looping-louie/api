"""Model-count registry used by provider responses."""

from typing import Protocol


class ModelRegistryService(Protocol):
    """Returns the number of Looping Louie models per provider."""

    def count_by_provider(self, provider: str) -> int:
        """Return the configured model count."""


class StaticModelRegistryService:
    """Small environment-configured model registry for the MVP."""

    def __init__(self, counts: dict[str, int] | None = None) -> None:
        """Store provider model counts."""

        self._counts = counts or {}

    def count_by_provider(self, provider: str) -> int:
        """Return the configured model count or zero."""

        return self._counts.get(provider, 0)
