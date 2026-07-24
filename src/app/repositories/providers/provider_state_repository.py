"""Provider state adapter used by model availability."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from src.app.catalogs.providers import (
    ProviderCatalogEntry,
    ProviderId,
)
from src.app.models.providers import ProviderCredential
from src.app.services.model_service import ProviderConnectionState

from .provider_repository import ProviderRepository


class ProviderStateRepositoryAdapter:
    """Exposes provider credentials as model availability states."""

    def __init__(
        self,
        *,
        provider_repository: ProviderRepository,
        catalog: Sequence[ProviderCatalogEntry],
    ) -> None:
        """Index the catalog and store the credential repository."""

        self._provider_repository = provider_repository
        self._catalog_by_id = {
            entry.id: entry
            for entry in catalog
        }

    async def get_states(
        self,
        *,
        workspace_id: str,
        provider_ids: Sequence[ProviderId],
    ) -> Mapping[ProviderId, ProviderConnectionState]:
        """Return requested provider states using one repository query."""

        credentials = await self._provider_repository.list_for_workspace(
            workspace_id,
        )
        credentials_by_provider = {
            credential.provider: credential
            for credential in credentials
        }

        states: dict[ProviderId, ProviderConnectionState] = {}

        for provider_id in self._unique_provider_ids(provider_ids):
            definition = self._catalog_by_id.get(provider_id)

            if definition is None:
                continue

            credential = credentials_by_provider.get(
                provider_id.value,
            )
            configured = self._is_configured(
                definition=definition,
                credential=credential,
            )

            states[provider_id] = ProviderConnectionState(
                provider_id=provider_id,
                configured=configured,
                enabled=bool(
                    configured
                    and credential is not None
                    and credential.enabled
                ),
            )

        return states

    @staticmethod
    def _is_configured(
        *,
        definition: ProviderCatalogEntry,
        credential: ProviderCredential | None,
    ) -> bool:
        """Return whether a credential satisfies its provider definition."""

        if credential is None or not credential.base_url:
            return False

        if definition.requires_api_key:
            return credential.key_ciphertext is not None

        return True

    @staticmethod
    def _unique_provider_ids(
        provider_ids: Sequence[ProviderId],
    ) -> tuple[ProviderId, ...]:
        """Deduplicate provider identifiers while preserving order."""

        unique_ids: list[ProviderId] = []
        seen: set[ProviderId] = set()

        for provider_id in provider_ids:
            if provider_id in seen:
                continue

            seen.add(provider_id)
            unique_ids.append(provider_id)

        return tuple(unique_ids)
