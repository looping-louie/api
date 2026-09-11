from __future__ import annotations

from datetime import UTC, datetime

from src.app.catalogs.providers import ProviderId
from src.app.models.linked_service import LinkedService


class FakeProviderStateRepository:
    """In-memory Linked Service repository for model availability tests."""

    def __init__(self) -> None:
        self._services: dict[tuple[str, ProviderId], LinkedService] = {}
        self.calls: list[str] = []

    def seed(
        self,
        *,
        project_id: str = 'workspace-1',
        user_id: str = 'user-1',
        state: object,
    ) -> None:
        """Register a service derived from a test provider state."""

        provider_id = getattr(state, 'provider_id')
        configured = getattr(state, 'configured')
        enabled = getattr(state, 'enabled')
        now = datetime(2026, 1, 1, tzinfo=UTC)

        self._services[(project_id, provider_id)] = LinkedService(
            id=f'{provider_id.value}-service',
            user_id=user_id,
            name=provider_id.value,
            provider_type=provider_id.value,
            enabled=enabled,
            key_trimmed=None,
            key_ciphertext=None,
            key_version=0,
            base_url='https://provider.example' if configured else None,
            version=1,
            created_at=now,
            updated_at=now,
        )

    def remove(
        self,
        *,
        project_id: str,
        provider_id: ProviderId,
    ) -> None:
        """Remove a provider state."""

        self._services.pop((project_id, provider_id), None)

    async def list_for_user(
        self,
        user_id: str,
    ) -> list[LinkedService]:
        """Return test services owned by the requested User."""

        self.calls.append(user_id)
        return [
            service
            for (service_project_id, _), service in self._services.items()
            if service.user_id == user_id
        ]
