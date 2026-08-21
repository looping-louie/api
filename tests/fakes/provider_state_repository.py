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
        workspace_id: str,
        state: object,
    ) -> None:
        """Register a service derived from a test provider state."""

        provider_id = getattr(state, 'provider_id')
        configured = getattr(state, 'configured')
        enabled = getattr(state, 'enabled')
        now = datetime(2026, 1, 1, tzinfo=UTC)

        self._services[(workspace_id, provider_id)] = LinkedService(
            id=f'{provider_id.value}-service',
            workspace_id=workspace_id,
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
        workspace_id: str,
        provider_id: ProviderId,
    ) -> None:
        """Remove a provider state."""

        self._services.pop((workspace_id, provider_id), None)

    async def list_for_workspace(self, workspace_id: str) -> list[LinkedService]:
        """Return all test services for the requested workspace."""

        self.calls.append(workspace_id)
        return [
            service
            for (service_workspace_id, _), service in self._services.items()
            if service_workspace_id == workspace_id
        ]
