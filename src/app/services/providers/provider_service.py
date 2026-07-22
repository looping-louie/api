"""Application service for model provider configuration."""

from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from src.app.models.providers import (
    ProviderCredential,
    ProviderDefinition,
    ProviderState,
    ProviderTestResult,
)
from src.app.repositories.provider_repository import ProviderRepository
from src.app.services.shared.tenant_service import TenantService

from .model_registry_service import ModelRegistryService
from .provider_connection_service import ProviderConnectionService
from .secret_service import SecretService


Clock = Callable[[], datetime]
IdFactory = Callable[[], str]


class ProviderError(Exception):
    """Base error for provider operations."""


class UnknownProviderError(ProviderError):
    """Raised when a provider is not part of the curated catalog."""

    def __init__(self, *, provider_id: str) -> None:
        super().__init__(f"Unknown provider '{provider_id}'.")
        self.provider_id = provider_id


class ProviderConfigurationError(ProviderError):
    """Raised when stored or supplied provider configuration is invalid."""

    def __init__(
        self,
        *,
        provider_id: str,
        reason: str,
    ) -> None:
        super().__init__(
            f"Provider '{provider_id}' configuration is invalid: {reason}."
        )
        self.provider_id = provider_id
        self.reason = reason


class ProviderNotConfiguredError(ProviderError):
    """Raised when an operation requires stored provider configuration."""

    def __init__(self, *, provider_id: str) -> None:
        super().__init__(
            f"Provider '{provider_id}' is not configured."
        )
        self.provider_id = provider_id


PROVIDERS: tuple[ProviderDefinition, ...] = (
    ProviderDefinition(
        provider="anthropic",
        name="Anthropic",
        description=(
            "Access Claude models for reasoning, coding and "
            "long-context review."
        ),
        logo_url="/images/providers/anthropic.jpeg",
        requires_api_key=True,
        default_base_url="https://api.anthropic.com/v1",
    ),
    ProviderDefinition(
        provider="nvidia",
        name="NVIDIA",
        description=(
            "Access NVIDIA-hosted open models through the NVIDIA NIM API."
        ),
        logo_url="/images/providers/nvidia.jpeg",
        requires_api_key=True,
        default_base_url="https://integrate.api.nvidia.com/v1",
    ),
    ProviderDefinition(
        provider="ollama",
        name="Ollama",
        description=(
            "Connect local or self-hosted open-source models through "
            "an Ollama endpoint."
        ),
        logo_url="/images/providers/ollama.jpeg",
        requires_api_key=False,
        default_base_url="http://localhost:11434",
    ),
    ProviderDefinition(
        provider="openai",
        name="OpenAI",
        description=(
            "Access GPT models for generation, reasoning and "
            "specialised reviews."
        ),
        logo_url="/images/providers/openai.jpeg",
        requires_api_key=True,
        default_base_url="https://api.openai.com/v1",
    ),
    ProviderDefinition(
        provider="together",
        name="Together",
        description=(
            "Access a broad catalogue of hosted open-source models."
        ),
        logo_url="/images/providers/together.jpeg",
        requires_api_key=True,
        default_base_url="https://api.together.xyz/v1",
    ),
)

PROVIDERS_BY_ID: dict[str, ProviderDefinition] = {
    definition.provider: definition
    for definition in PROVIDERS
}


class ProviderService:
    """Coordinates provider configuration, storage and testing."""

    def __init__(
        self,
        *,
        repository: ProviderRepository,
        tenant_service: TenantService,
        secret_service: SecretService,
        connection_service: ProviderConnectionService,
        model_registry: ModelRegistryService,
        clock: Clock | None = None,
        id_factory: IdFactory | None = None,
    ) -> None:
        self._repository = repository
        self._tenant_service = tenant_service
        self._secret_service = secret_service
        self._connection_service = connection_service
        self._model_registry = model_registry
        self._clock = clock or self._default_clock
        self._id_factory = id_factory or self._default_id_factory

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
    ) -> list[ProviderState]:
        """Return every supported provider and its workspace state."""

        workspace_id, _ = await self._resolve_tenant(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        credentials = await self._repository.list_for_workspace(
            workspace_id,
        )
        credentials_by_provider = {
            credential.provider: credential
            for credential in credentials
        }

        return [
            self._build_state(
                definition=definition,
                credential=credentials_by_provider.get(
                    definition.provider,
                ),
            )
            for definition in PROVIDERS
        ]

    async def describe(
        self,
        *,
        user_id: str,
        provider_id: str,
        requested_workspace_id: str | None = None,
    ) -> ProviderState:
        """Return one provider and its workspace configuration state."""

        definition = self._get_definition(provider_id)
        workspace_id, _ = await self._resolve_tenant(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        credential = await self._repository.get(
            workspace_id,
            definition.provider,
        )

        return self._build_state(
            definition=definition,
            credential=credential,
        )

    async def configure(
        self,
        *,
        user_id: str,
        provider_id: str,
        api_key: str | None,
        base_url: str | None,
        requested_workspace_id: str | None = None,
    ) -> ProviderState:
        """Create or replace provider configuration."""

        definition = self._get_definition(provider_id)
        workspace_id, actor_user_id = await self._resolve_tenant(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        current = await self._repository.get(
            workspace_id,
            definition.provider,
        )

        clean_api_key = self._clean_optional_value(api_key)
        clean_base_url = self._resolve_base_url(
            supplied=base_url,
            current=current,
            definition=definition,
        )

        key_ciphertext = (
            current.key_ciphertext
            if current is not None
            else None
        )
        key_trimmed = (
            current.key_trimmed
            if current is not None
            else None
        )

        if clean_api_key is not None:
            key_ciphertext = self._secret_service.encrypt_secret(
                clean_api_key,
            )
            key_trimmed = self._secret_service.trim_secret(
                clean_api_key,
            )

        self._validate_configuration(
            definition=definition,
            key_ciphertext=key_ciphertext,
            base_url=clean_base_url,
        )

        await self._test_configuration(
            definition=definition,
            key_ciphertext=key_ciphertext,
            plaintext_api_key=clean_api_key,
            base_url=clean_base_url,
        )

        now = self._clock()
        credential = ProviderCredential(
            id=(
                current.id
                if current is not None
                else self._id_factory()
            ),
            workspace_id=workspace_id,
            provider=definition.provider,
            enabled=True,
            enabled_by=actor_user_id,
            enabled_on=now,
            key_trimmed=key_trimmed,
            key_ciphertext=key_ciphertext,
            key_version=(
                current.key_version
                if current is not None
                else 1
            ),
            base_url=clean_base_url,
            created_at=(
                current.created_at
                if current is not None
                else now
            ),
            updated_at=now,
        )
        stored = await self._repository.upsert(credential)

        return self._build_state(
            definition=definition,
            credential=stored,
        )

    async def enable(
        self,
        *,
        user_id: str,
        provider_id: str,
        requested_workspace_id: str | None = None,
    ) -> ProviderState:
        """Enable a configured provider."""

        return await self._set_enabled(
            user_id=user_id,
            provider_id=provider_id,
            enabled=True,
            requested_workspace_id=requested_workspace_id,
        )

    async def disable(
        self,
        *,
        user_id: str,
        provider_id: str,
        requested_workspace_id: str | None = None,
    ) -> ProviderState:
        """Disable a provider without deleting its credentials."""

        return await self._set_enabled(
            user_id=user_id,
            provider_id=provider_id,
            enabled=False,
            requested_workspace_id=requested_workspace_id,
        )

    async def delete(
        self,
        *,
        user_id: str,
        provider_id: str,
        requested_workspace_id: str | None = None,
    ) -> None:
        """Delete stored configuration and encrypted credentials."""

        definition = self._get_definition(provider_id)
        workspace_id, _ = await self._resolve_tenant(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        await self._repository.unset(
            workspace_id=workspace_id,
            provider=definition.provider,
            updated_at=self._clock(),
        )

    async def test(
        self,
        *,
        user_id: str,
        provider_id: str,
        requested_workspace_id: str | None = None,
    ) -> ProviderTestResult:
        """Test one stored provider configuration."""

        definition = self._get_definition(provider_id)
        workspace_id, _ = await self._resolve_tenant(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        credential = await self._require_credential(
            workspace_id=workspace_id,
            definition=definition,
        )

        self._validate_configuration(
            definition=definition,
            key_ciphertext=credential.key_ciphertext,
            base_url=credential.base_url,
        )

        started_at = perf_counter()

        await self._test_configuration(
            definition=definition,
            key_ciphertext=credential.key_ciphertext,
            plaintext_api_key=None,
            base_url=credential.base_url,
        )

        latency_ms = round(
            (perf_counter() - started_at) * 1000,
        )

        return ProviderTestResult(
            provider=definition.provider,
            success=True,
            message="Provider connection succeeded.",
            latency_ms=latency_ms,
        )

    async def _set_enabled(
        self,
        *,
        user_id: str,
        provider_id: str,
        enabled: bool,
        requested_workspace_id: str | None,
    ) -> ProviderState:
        definition = self._get_definition(provider_id)
        workspace_id, actor_user_id = await self._resolve_tenant(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        credential = await self._require_credential(
            workspace_id=workspace_id,
            definition=definition,
        )

        if enabled:
            self._validate_configuration(
                definition=definition,
                key_ciphertext=credential.key_ciphertext,
                base_url=credential.base_url,
            )

        now = self._clock()
        stored = await self._repository.set_enabled(
            workspace_id=workspace_id,
            provider=definition.provider,
            enabled=enabled,
            enabled_by=actor_user_id if enabled else None,
            enabled_on=now if enabled else None,
            updated_at=now,
        )

        return self._build_state(
            definition=definition,
            credential=stored,
        )

    async def _require_credential(
        self,
        *,
        workspace_id: str,
        definition: ProviderDefinition,
    ) -> ProviderCredential:
        credential = await self._repository.get(
            workspace_id,
            definition.provider,
        )

        if credential is None:
            raise ProviderNotConfiguredError(
                provider_id=definition.provider,
            )

        return credential

    async def _test_configuration(
        self,
        *,
        definition: ProviderDefinition,
        key_ciphertext: str | None,
        plaintext_api_key: str | None,
        base_url: str | None,
    ) -> None:
        api_key = plaintext_api_key

        try:
            if api_key is None and key_ciphertext is not None:
                api_key = self._secret_service.decrypt_secret(
                    key_ciphertext,
                )

            await self._connection_service.test_connection(
                provider=definition.provider,
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
        tenant = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return tenant.workspace_id, tenant.user_id

    def _build_state(
        self,
        *,
        definition: ProviderDefinition,
        credential: ProviderCredential | None,
    ) -> ProviderState:
        configured = self._is_configured(
            definition=definition,
            credential=credential,
        )

        return ProviderState(
            provider=definition.provider,
            name=definition.name,
            description=definition.description,
            logo_url=definition.logo_url,
            requires_api_key=definition.requires_api_key,
            configured=configured,
            enabled=bool(
                credential
                and credential.enabled
                and configured
            ),
            key_trimmed=(
                credential.key_trimmed
                if credential is not None
                else None
            ),
            base_url=(
                credential.base_url
                if credential is not None
                else definition.default_base_url
            ),
            model_count=self._model_registry.count_by_provider(
                definition.provider,
            ),
        )

    @staticmethod
    def _get_definition(provider_id: str) -> ProviderDefinition:
        normalized_provider_id = provider_id.strip().casefold()
        definition = PROVIDERS_BY_ID.get(normalized_provider_id)

        if definition is None:
            raise UnknownProviderError(
                provider_id=normalized_provider_id or provider_id,
            )

        return definition

    @staticmethod
    def _resolve_base_url(
        *,
        supplied: str | None,
        current: ProviderCredential | None,
        definition: ProviderDefinition,
    ) -> str | None:
        clean_supplied = ProviderService._clean_optional_value(
            supplied,
        )

        if clean_supplied is not None:
            return clean_supplied.rstrip("/")

        if current is not None and current.base_url:
            return current.base_url.rstrip("/")

        return definition.default_base_url

    @staticmethod
    def _validate_configuration(
        *,
        definition: ProviderDefinition,
        key_ciphertext: str | None,
        base_url: str | None,
    ) -> None:
        if definition.requires_api_key and key_ciphertext is None:
            raise ProviderConfigurationError(
                provider_id=definition.provider,
                reason="an API key is required",
            )

        if base_url is None:
            raise ProviderConfigurationError(
                provider_id=definition.provider,
                reason="a base URL is required",
            )

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
    def _clean_optional_value(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _default_clock() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _default_id_factory() -> str:
        return uuid4().hex
