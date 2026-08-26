"""Application service for user-owned linked services."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from src.app.catalogs.models import CATALOG_INDEX, MODEL_CATALOG, ModelStatus
from src.app.catalogs.providers import ProviderCatalogEntry
from src.app.models.linked_service import LinkedService
from src.app.repositories.linked_services import LinkedServiceRepository
from src.app.services.providers.configuration import (
    clean_optional_value,
    find_provider_definition,
    resolve_base_url,
    validate_configuration,
)
from src.app.services.providers.connection import ProviderConnectionService
from src.app.services.providers.errors import UnknownProviderError
from src.app.services.providers.secret import SecretService
from src.app.services.shared.tenant import TenantService
from src.app.services.shared.dependency_checker import DependencyChecker
from src.app.services.shared.reference_resolver import ResourceReference
from src.app.services.users import UserService


Clock = Callable[[], datetime]
IdFactory = Callable[[], str]


class LinkedServiceNotFoundError(Exception):
    """Raised when a linked service is absent from the selected user."""

    def __init__(self, service_id: str) -> None:
        super().__init__(f"Linked service '{service_id}' was not found.")
        self.service_id = service_id


class LinkedServiceNameConflictError(Exception):
    """Raised when a user already owns the requested service name."""

    def __init__(self, name: str) -> None:
        """Store the conflicting linked-service name."""

        super().__init__(f"A linked service named '{name}' already exists.")
        self.name = name


class LinkedServiceSelectionUnavailableError(Exception):
    """Raised when a linked service cannot serve a selected logical model."""

    def __init__(self, *, service_id: str, reason: str) -> None:
        """Store the unavailable linked-service identity and reason."""

        super().__init__(f"Linked service '{service_id}' {reason}.")
        self.service_id = service_id
        self.reason = reason


class LinkedServiceService:
    """Coordinate linked-service configuration, testing, and persistence."""

    def __init__(
        self,
        *,
        repository: LinkedServiceRepository,
        user_service: UserService,
        tenant_service: TenantService,
        secret_service: SecretService,
        connection_service: ProviderConnectionService,
        catalog: Sequence[ProviderCatalogEntry],
        dependency_checker: DependencyChecker | None = None,
        clock: Clock | None = None,
        id_factory: IdFactory | None = None,
    ) -> None:
        """Store infrastructure and curated provider definitions."""
        self._repository = repository
        self._user_service = user_service
        self._tenant_service = tenant_service
        self._secret_service = secret_service
        self._connection_service = connection_service
        self._catalog_by_id = {entry.id: entry for entry in catalog}
        self._dependency_checker = dependency_checker
        self._clock = clock or self._default_clock
        self._id_factory = id_factory or self._default_id_factory

    async def list(self, *, user_id: str) -> list[LinkedService]:
        """List linked services owned by the registered user."""
        await self._user_service.get(user_id=user_id)
        return await self._repository.list_for_user(user_id)

    async def get(self, *, user_id: str, service_id: str) -> LinkedService:
        """Return one linked service owned by the registered user."""
        await self._user_service.get(user_id=user_id)
        return await self._get_required_for_user(user_id, service_id)

    async def create(
        self, *, user_id: str, name: str, provider_type: str, api_key: str | None,
        base_url: str | None, enabled: bool,
    ) -> LinkedService:
        """Create and test a new linked service before it is stored."""
        await self._user_service.get(user_id=user_id)
        definition = self._definition(provider_type)
        await self._require_unique_name(user_id, name)
        plaintext_api_key = clean_optional_value(api_key)
        key_ciphertext = self._encrypt(plaintext_api_key)
        resolved_base_url = resolve_base_url(
            definition=definition, current=None, supplied=base_url, supplied_explicitly=True,
        )
        validate_configuration(definition=definition, key_ciphertext=key_ciphertext, base_url=resolved_base_url)
        await self._test(definition, key_ciphertext, plaintext_api_key, resolved_base_url)
        now = self._clock()
        return await self._repository.create(LinkedService(
            id=self._id_factory(), user_id=user_id, name=name,
            provider_type=definition.id.value, enabled=enabled,
            key_trimmed=self._trim(plaintext_api_key), key_ciphertext=key_ciphertext,
            key_version=1, base_url=resolved_base_url, version=1,
            created_at=now, updated_at=now,
        ))

    async def patch(
        self, *, user_id: str, service_id: str, name: str | None, api_key: str | None,
        api_key_supplied: bool, base_url: str | None, base_url_supplied: bool,
        enabled: bool | None,
    ) -> LinkedService:
        """Update mutable linked-service fields and test changed configurations."""
        await self._user_service.get(user_id=user_id)
        current = await self._get_required_for_user(user_id, service_id)
        if name is not None and name != current.name:
            await self._require_unique_name(user_id, name)
        definition = self._definition(current.provider_type)
        plaintext_api_key = clean_optional_value(api_key) if api_key_supplied else None
        key_ciphertext = self._encrypt(plaintext_api_key) if api_key_supplied else current.key_ciphertext
        key_trimmed = self._trim(plaintext_api_key) if api_key_supplied else current.key_trimmed
        resolved_base_url = resolve_base_url(
            definition=definition, current=current, supplied=base_url,
            supplied_explicitly=base_url_supplied,
        )
        target_enabled = current.enabled if enabled is None else enabled
        configuration_changed = api_key_supplied or base_url_supplied
        enabling = target_enabled and not current.enabled
        if configuration_changed or enabling:
            validate_configuration(definition=definition, key_ciphertext=key_ciphertext, base_url=resolved_base_url)
            await self._test(definition, key_ciphertext, plaintext_api_key, resolved_base_url)
        updated = replace(
            current, name=current.name if name is None else name, enabled=target_enabled,
            key_trimmed=key_trimmed, key_ciphertext=key_ciphertext, base_url=resolved_base_url,
            version=current.version + 1, updated_at=self._clock(),
        )
        return await self._repository.update(updated)

    async def delete(self, *, user_id: str, service_id: str) -> None:
        """Delete one linked service owned by the registered user."""
        await self._user_service.get(user_id=user_id)
        if self._dependency_checker is not None:
            workspace_id = await self._workspace_id(user_id, None)
            await self._dependency_checker.require_deletable(
                workspace_id=workspace_id,
                target=ResourceReference('linked_service', service_id),
            )
        if not await self._repository.delete_for_user(user_id, service_id):
            raise LinkedServiceNotFoundError(service_id)

    async def require_available_selection_for_user(
        self,
        *,
        user_id: str,
        service_id: str,
        model_id: str,
    ) -> None:
        """Require a user-owned service with an active model deployment."""

        linked_service = await self._get_required_for_user(user_id, service_id)
        self._require_available(linked_service, service_id, model_id)

    async def require_available_selection(
        self,
        *,
        workspace_id: str,
        service_id: str,
        model_id: str,
    ) -> None:
        """Validate a workspace caller through its selected workspace owner.

        This adapter preserves existing workspace-scoped Activity, Pipeline, and
        default validation until those contracts move to user ownership.
        """

        linked_service = await self._get_required_for_workspace(workspace_id, service_id)
        self._require_available(linked_service, service_id, model_id)

    def _require_available(
        self,
        linked_service: LinkedService,
        service_id: str,
        model_id: str,
    ) -> None:
        """Require a linked service to support one active model deployment."""

        if not linked_service.enabled:
            raise LinkedServiceSelectionUnavailableError(
                service_id=service_id,
                reason='is disabled',
            )
        if not self.is_configured(linked_service):
            raise LinkedServiceSelectionUnavailableError(
                service_id=service_id,
                reason='is not configured',
            )
        if model_id not in self.available_models(linked_service.provider_type):
            raise LinkedServiceSelectionUnavailableError(
                service_id=service_id,
                reason=f"does not have an active deployment for model '{model_id}'",
            )

    def available_models(self, provider_type: str) -> list[str]:
        """Return active logical model IDs deployed by a provider type."""

        return [
            model.id
            for model in MODEL_CATALOG
            if model.status != ModelStatus.DEPRECATED
            and any(
                offering.provider_id.value == provider_type
                and offering.status != ModelStatus.DEPRECATED
                for offering in CATALOG_INDEX.offerings_for_model(model.id)
            )
        ]

    def is_configured(self, linked_service: LinkedService) -> bool:
        """Return whether a linked service has its required settings."""
        from src.app.services.providers.configuration import is_configured
        return is_configured(
            definition=self._definition(linked_service.provider_type),
            credential=linked_service,
        )

    async def _workspace_id(self, user_id: str, requested_workspace_id: str | None) -> str:
        """Resolve the selected workspace for a user operation."""
        tenant = await self._tenant_service.resolve(user_id=user_id, requested_workspace_id=requested_workspace_id)
        return tenant.workspace_id

    async def _get_required_for_user(self, user_id: str, service_id: str) -> LinkedService:
        """Load a service or raise the stable not-found error."""
        linked_service = await self._repository.get_for_user(user_id, service_id)
        if linked_service is None:
            raise LinkedServiceNotFoundError(service_id)
        return linked_service

    async def _get_required_for_workspace(self, workspace_id: str, service_id: str) -> LinkedService:
        """Load a user-owned service through a temporary workspace adapter."""
        linked_service = await self._repository.get_for_workspace_owner(
            workspace_id,
            service_id,
        )
        if linked_service is None:
            raise LinkedServiceNotFoundError(service_id)
        return linked_service

    async def _require_unique_name(
        self,
        user_id: str,
        name: str,
    ) -> None:
        """Reject a duplicate linked-service name for one user."""

        existing = await self._repository.get_by_name(user_id, name)
        if existing is not None:
            raise LinkedServiceNameConflictError(name)

    def _definition(self, provider_type: str) -> ProviderCatalogEntry:
        """Resolve a provider definition from the curated catalog."""
        definition = find_provider_definition(provider_type, self._catalog_by_id)
        if definition is None:
            raise UnknownProviderError(provider_id=provider_type.strip().casefold() or provider_type)
        return definition

    def _encrypt(self, api_key: str | None) -> str | None:
        """Encrypt a supplied key while preserving a null value."""
        return self._secret_service.encrypt_secret(api_key) if api_key is not None else None

    def _trim(self, api_key: str | None) -> str | None:
        """Build a safe key preview while preserving a null value."""
        return self._secret_service.trim_secret(api_key) if api_key is not None else None

    async def _test(self, definition: ProviderCatalogEntry, key_ciphertext: str | None, plaintext_api_key: str | None, base_url: str | None) -> None:
        """Test candidate settings without retaining plaintext credentials."""
        api_key = plaintext_api_key
        try:
            if api_key is None and key_ciphertext is not None:
                api_key = self._secret_service.decrypt_secret(key_ciphertext)
            await self._connection_service.test_connection(provider=definition.id, api_key=api_key, base_url=base_url)
        finally:
            api_key = None

    @staticmethod
    def _default_clock() -> datetime:
        """Return the current UTC timestamp."""
        return datetime.now(UTC)

    @staticmethod
    def _default_id_factory() -> str:
        """Create a linked-service identifier."""
        return uuid4().hex
