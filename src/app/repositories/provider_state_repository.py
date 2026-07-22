"""Provider state adapter used by model availability."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from src.app.catalogs.models import ProviderId
from src.app.models.providers import (
    ProviderCredential,
    ProviderDefinition,
)
from src.app.repositories.provider_repository import ProviderRepository
from src.app.services.model_service import ProviderConnectionState
from src.app.services.providers.provider_service import PROVIDERS_BY_ID


class ProviderStateRepositoryAdapter:
    """Exposes provider credentials as model availability states."""

    def __init__(
        self,
        *,
        provider_repository: ProviderRepository,
    ) -> None:
        self._provider_repository = provider_repository

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
            definition = PROVIDERS_BY_ID.get(
                provider_id.value,
            )

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
        definition: ProviderDefinition,
        credential: ProviderCredential | None,
    ) -> bool:
        if credential is None or not credential.base_url:
            return False

        if definition.requires_api_key:
            return credential.key_ciphertext is not None

        return True

    @staticmethod
    def _unique_provider_ids(
        provider_ids: Sequence[ProviderId],
    ) -> tuple[ProviderId, ...]:
        unique_ids: list[ProviderId] = []
        seen: set[ProviderId] = set()

        for provider_id in provider_ids:
            if provider_id in seen:
                continue

            seen.add(provider_id)
            unique_ids.append(provider_id)

        return tuple(unique_ids)
