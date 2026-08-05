"""Application service for workspace provider configuration."""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from uuid import uuid4

from src.app.catalogs.providers import ProviderCatalogEntry
from src.app.models.provider import ProviderCredential, ProviderState
from src.app.repositories.providers.provider_repository import (
    ProviderRepository,
)
from src.app.services.shared.tenant import TenantService

from .model_registry import ModelRegistryService
from .configuration import (
    build_provider_state,
    clean_optional_value,
    find_provider_definition,
    resolve_base_url,
    validate_configuration,
)
from .connection import ProviderConnectionService
from .errors import UnknownProviderError
from .secret import SecretService


Clock = Callable[[], datetime]
IdFactory = Callable[[], str]


class ProviderService:
    """Coordinate provider configuration, storage, and connection checks."""

    def __init__(
        self,
        *,
        repository: ProviderRepository,
        tenant_service: TenantService,
        secret_service: SecretService,
        connection_service: ProviderConnectionService,
        model_registry: ModelRegistryService,
        catalog: Sequence[ProviderCatalogEntry],
        clock: Clock | None = None,
        id_factory: IdFactory | None = None,
    ) -> None:
        """Store provider infrastructure and curated definitions."""

        self._repository = repository
        self._tenant_service = tenant_service
        self._secret_service = secret_service
        self._connection_service = connection_service
        self._model_registry = model_registry
        self._catalog = tuple(catalog)
        self._catalog_by_id = {entry.id: entry for entry in self._catalog}
        self._clock = clock or self._default_clock
        self._id_factory = id_factory or self._default_id_factory

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
    ) -> list[ProviderState]:
        """Return every catalog provider and its workspace state."""

        workspace_id, _ = await self._resolve_tenant(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        credentials = await self._repository.list_for_workspace(workspace_id)
        credentials_by_provider = {
            credential.provider: credential
            for credential in credentials
        }
        return [
            self._build_state(
                definition,
                credentials_by_provider.get(definition.id.value),
            )
            for definition in self._catalog
        ]

    async def get(
        self,
        *,
        user_id: str,
        provider_id: str,
        requested_workspace_id: str | None = None,
    ) -> ProviderState:
        """Return one catalog provider and its workspace state."""

        definition = self._get_definition(provider_id)
        workspace_id, _ = await self._resolve_tenant(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        credential = await self._repository.get(
            workspace_id,
            definition.id.value,
        )
        return self._build_state(definition, credential)

    async def patch(
        self,
        *,
        user_id: str,
        provider_id: str,
        api_key: str | None,
        api_key_supplied: bool,
        base_url: str | None,
        base_url_supplied: bool,
        enabled: bool | None,
        requested_workspace_id: str | None = None,
    ) -> ProviderState:
        """Patch workspace configuration for a catalog provider."""

        definition = self._get_definition(provider_id)
        workspace_id, actor_user_id = await self._resolve_tenant(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        current = await self._repository.get(
            workspace_id,
            definition.id.value,
        )
        key_ciphertext = current.key_ciphertext if current else None
        key_trimmed = current.key_trimmed if current else None
        plaintext_api_key = None

        if api_key_supplied:
            plaintext_api_key = clean_optional_value(api_key)
            key_ciphertext = None
            key_trimmed = None
            if plaintext_api_key is not None:
                key_ciphertext = self._secret_service.encrypt_secret(
                    plaintext_api_key
                )
                key_trimmed = self._secret_service.trim_secret(
                    plaintext_api_key
                )

        resolved_base_url = resolve_base_url(
            definition=definition,
            current=current,
            supplied=base_url,
            supplied_explicitly=base_url_supplied,
        )
        target_enabled = (
            enabled
            if enabled is not None
            else current.enabled
            if current is not None
            else True
        )
        configuration_changed = api_key_supplied or base_url_supplied

        # New, changed, or enabled configurations must be usable before save.
        if current is None or configuration_changed or target_enabled:
            validate_configuration(
                definition=definition,
                key_ciphertext=key_ciphertext,
                base_url=resolved_base_url,
            )

        enabling = bool(
            target_enabled
            and (current is None or not current.enabled)
        )
        if configuration_changed or enabling:
            await self._test_configuration(
                definition=definition,
                key_ciphertext=key_ciphertext,
                plaintext_api_key=plaintext_api_key,
                base_url=resolved_base_url,
            )

        now = self._clock()
        stored = await self._repository.upsert(
            ProviderCredential(
                id=current.id if current else self._id_factory(),
                workspace_id=workspace_id,
                provider=definition.id.value,
                enabled=target_enabled,
                enabled_by=actor_user_id if target_enabled else None,
                enabled_on=now if target_enabled else None,
                key_trimmed=key_trimmed,
                key_ciphertext=key_ciphertext,
                key_version=current.key_version if current else 1,
                base_url=resolved_base_url,
                created_at=current.created_at if current else now,
                updated_at=now,
            )
        )
        return self._build_state(definition, stored)

    async def delete(
        self,
        *,
        user_id: str,
        provider_id: str,
        requested_workspace_id: str | None = None,
    ) -> None:
        """Delete stored workspace configuration for a catalog provider."""

        definition = self._get_definition(provider_id)
        workspace_id, _ = await self._resolve_tenant(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        await self._repository.unset(
            workspace_id=workspace_id,
            provider=definition.id.value,
            updated_at=self._clock(),
        )

    async def _test_configuration(
        self,
        *,
        definition: ProviderCatalogEntry,
        key_ciphertext: str | None,
        plaintext_api_key: str | None,
        base_url: str | None,
    ) -> None:
        """Test candidate settings without retaining the plaintext secret."""

        api_key = plaintext_api_key
        try:
            if api_key is None and key_ciphertext is not None:
                api_key = self._secret_service.decrypt_secret(key_ciphertext)
            await self._connection_service.test_connection(
                provider=definition.id,
                api_key=api_key,
                base_url=base_url,
            )
        finally:
            api_key = None

    async def _resolve_tenant(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None,
    ) -> tuple[str, str]:
        """Resolve workspace and actor identifiers for an operation."""

        tenant = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        return tenant.workspace_id, tenant.user_id

    def _get_definition(self, provider_id: str) -> ProviderCatalogEntry:
        """Resolve a provider identifier against the curated catalog."""

        definition = find_provider_definition(
            provider_id,
            self._catalog_by_id,
        )
        if definition is None:
            normalized = provider_id.strip().casefold()
            raise UnknownProviderError(
                provider_id=normalized or provider_id
            )
        return definition

    def _build_state(
        self,
        definition: ProviderCatalogEntry,
        credential: ProviderCredential | None,
    ) -> ProviderState:
        """Build a safe state with catalog-derived model metadata."""

        return build_provider_state(
            definition=definition,
            credential=credential,
            model_count=self._model_registry.count_by_provider(definition.id),
        )

    @staticmethod
    def _default_clock() -> datetime:
        """Return the current UTC timestamp."""

        return datetime.now(UTC)

    @staticmethod
    def _default_id_factory() -> str:
        """Create a provider credential identifier."""

        return uuid4().hex
