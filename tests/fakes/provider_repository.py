"""In-memory provider credential repository."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime

from src.app.models.providers import ProviderCredential


class FakeProviderRepository:
    """Stores provider credentials in memory by workspace and provider."""

    def __init__(self) -> None:
        self._credentials: dict[
            tuple[str, str],
            ProviderCredential,
        ] = {}
        self.unset_calls: list[tuple[str, str, datetime]] = []

    @property
    def credentials(self) -> list[ProviderCredential]:
        """Return copies of all stored credentials."""

        return [
            deepcopy(credential)
            for credential in self._credentials.values()
        ]

    def seed(self, credential: ProviderCredential) -> None:
        """Insert a provider credential directly."""

        key = self._build_key(
            workspace_id=credential.workspace_id,
            provider=credential.provider,
        )
        self._credentials[key] = deepcopy(credential)

    async def list_for_workspace(
        self,
        workspace_id: str,
    ) -> list[ProviderCredential]:
        """Return all credentials belonging to one workspace."""

        return [
            deepcopy(credential)
            for credential in self._credentials.values()
            if credential.workspace_id == workspace_id
        ]

    async def get(
        self,
        workspace_id: str,
        provider: str,
    ) -> ProviderCredential | None:
        """Return one stored provider credential."""

        credential = self._credentials.get(
            self._build_key(
                workspace_id=workspace_id,
                provider=provider,
            )
        )

        if credential is None:
            return None

        return deepcopy(credential)

    async def upsert(
        self,
        credential: ProviderCredential,
    ) -> ProviderCredential:
        """Create or replace a provider credential."""

        key = self._build_key(
            workspace_id=credential.workspace_id,
            provider=credential.provider,
        )
        self._credentials[key] = deepcopy(credential)

        return deepcopy(credential)

    async def set_enabled(
        self,
        *,
        workspace_id: str,
        provider: str,
        enabled: bool,
        enabled_by: str | None,
        enabled_on: datetime | None,
        updated_at: datetime,
    ) -> ProviderCredential:
        """Change the enabled state of a stored credential."""

        key = self._build_key(
            workspace_id=workspace_id,
            provider=provider,
        )
        current = self._credentials.get(key)

        if current is None:
            raise AssertionError(
                f"Provider '{provider}' is not stored for '{workspace_id}'."
            )

        updated = replace(
            current,
            enabled=enabled,
            enabled_by=enabled_by,
            enabled_on=enabled_on,
            updated_at=updated_at,
        )
        self._credentials[key] = deepcopy(updated)

        return deepcopy(updated)

    async def unset(
        self,
        *,
        workspace_id: str,
        provider: str,
        updated_at: datetime,
    ) -> None:
        """Delete one provider credential."""

        self.unset_calls.append(
            (
                workspace_id,
                provider,
                updated_at,
            )
        )
        self._credentials.pop(
            self._build_key(
                workspace_id=workspace_id,
                provider=provider,
            ),
            None,
        )

    @staticmethod
    def _build_key(
        *,
        workspace_id: str,
        provider: str,
    ) -> tuple[str, str]:
        return workspace_id, provider.casefold()
