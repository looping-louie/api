"""Application service for model provider configuration."""

from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from src.app.models.providers import (
    ProviderCredential,
    ProviderDefinition,
    ProviderState,
    ProviderTestResult,
)
from src.app.repositories.provider_repository import ProviderRepository
from src.app.services.providers.model_registry_service import ModelRegistryService
from src.app.services.providers.provider_connection_service import (
    ProviderConnectionService,
)
from src.app.services.providers.request_context_service import RequestContextService
from src.app.services.providers.secret_service import SecretService


class ProviderError(Exception):
    """Base error for provider operations."""


class UnknownProviderError(ProviderError):
    """Raised when a provider is unsupported."""


class ProviderConfigurationError(ProviderError):
    """Raised when provider configuration is incomplete."""


class ProviderNotConfiguredError(ProviderError):
    """Raised when a provider has no stored configuration."""


PROVIDERS = (
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

PROVIDERS_BY_ID = {
    definition.provider: definition
    for definition in PROVIDERS
}


class ProviderService:
    """Coordinates provider configuration, storage and testing."""

    def __init__(
        self,
        repository: ProviderRepository,
        secret_service: SecretService,
        connection_service: ProviderConnectionService,
        model_registry: ModelRegistryService,
        request_context: RequestContextService,
    ) -> None:
        """Initialise the service with infrastructure dependencies."""

        self._repository = repository
        self._secret_service = secret_service
        self._connection_service = connection_service
        self._model_registry = model_registry
        self._request_context = request_context

    async def list_providers(self) -> list[ProviderState]:
        """Return provider metadata and current organisation state."""

        actor = self._request_context.get_current_actor()
        credentials = await self._repository.list_for_org(actor.org_id)
        credentials_by_provider = {
            credential.provider: credential
            for credential in credentials
        }

        return [
            self._build_state(
                definition=definition,
                credential=credentials_by_provider.get(
                    definition.provider
                ),
            )
            for definition in PROVIDERS
        ]

    async def set_provider(
        self,
        provider: str,
        api_key: str | None,
        base_url: str | None,
    ) -> ProviderState:
        """Create or replace provider configuration."""

        definition = self._get_definition(provider)
        actor = self._request_context.get_current_actor()
        current = await self._repository.get(
            actor.org_id,
            definition.provider,
        )

        clean_api_key = self._clean_optional_value(api_key)
        clean_base_url = self._resolve_base_url(
            supplied=base_url,
            current=current,
            definition=definition,
        )
        key_ciphertext = current.key_ciphertext if current else None
        key_trimmed = current.key_trimmed if current else None

        if clean_api_key is not None:
            key_ciphertext = self._secret_service.encrypt_secret(
                clean_api_key
            )
            key_trimmed = self._secret_service.trim_secret(
                clean_api_key
            )

        self._validate_configuration(
            definition=definition,
            key_ciphertext=key_ciphertext,
            base_url=clean_base_url,
        )

        plaintext_key = clean_api_key

        if plaintext_key is None and key_ciphertext is not None:
            plaintext_key = self._secret_service.decrypt_secret(
                key_ciphertext
            )

        try:
            await self._connection_service.test_connection(
                provider=definition.provider,
                api_key=plaintext_key,
                base_url=clean_base_url,
            )
        finally:
            plaintext_key = None

        now = datetime.now(timezone.utc)
        credential = ProviderCredential(
            id=current.id if current else uuid4().hex,
            org_id=actor.org_id,
            provider=definition.provider,
            enabled=True,
            enabled_by=actor.user_id,
            enabled_on=now,
            key_trimmed=key_trimmed,
            key_ciphertext=key_ciphertext,
            key_version=current.key_version if current else 1,
            base_url=clean_base_url,
            created_at=current.created_at if current else now,
            updated_at=now,
        )
        stored = await self._repository.upsert(credential)

        return self._build_state(
            definition=definition,
            credential=stored,
        )

    async def set_provider_enabled(
        self,
        provider: str,
        enabled: bool,
    ) -> ProviderState:
        """Enable or disable stored provider configuration."""

        definition = self._get_definition(provider)
        actor = self._request_context.get_current_actor()
        credential = await self._repository.get(
            actor.org_id,
            definition.provider,
        )

        if credential is None:
            raise ProviderNotConfiguredError(
                f"Provider '{definition.provider}' is not configured."
            )

        if enabled:
            self._validate_configuration(
                definition=definition,
                key_ciphertext=credential.key_ciphertext,
                base_url=credential.base_url,
            )

        now = datetime.now(timezone.utc)
        stored = await self._repository.set_enabled(
            org_id=actor.org_id,
            provider=definition.provider,
            enabled=enabled,
            enabled_by=actor.user_id,
            enabled_on=now if enabled else None,
            updated_at=now,
        )

        return self._build_state(
            definition=definition,
            credential=stored,
        )

    async def unset_provider(self, provider: str) -> None:
        """Delete stored provider configuration."""

        definition = self._get_definition(provider)
        actor = self._request_context.get_current_actor()

        await self._repository.unset(
            org_id=actor.org_id,
            provider=definition.provider,
            updated_at=datetime.now(timezone.utc),
        )

    async def test_provider(
        self,
        provider: str,
    ) -> ProviderTestResult:
        """Test one stored provider configuration."""

        definition = self._get_definition(provider)
        actor = self._request_context.get_current_actor()
        credential = await self._repository.get(
            actor.org_id,
            definition.provider,
        )

        if credential is None:
            raise ProviderNotConfiguredError(
                f"Provider '{definition.provider}' is not configured."
            )

        self._validate_configuration(
            definition=definition,
            key_ciphertext=credential.key_ciphertext,
            base_url=credential.base_url,
        )

        api_key: str | None = None
        started_at = perf_counter()

        try:
            if credential.key_ciphertext is not None:
                api_key = self._secret_service.decrypt_secret(
                    credential.key_ciphertext
                )

            await self._connection_service.test_connection(
                provider=definition.provider,
                api_key=api_key,
                base_url=credential.base_url,
            )
        finally:
            api_key = None

        latency_ms = round(
            (perf_counter() - started_at) * 1000
        )

        return ProviderTestResult(
            provider=definition.provider,
            success=True,
            message="Provider connection succeeded.",
            latency_ms=latency_ms,
        )

    @staticmethod
    def _get_definition(provider: str) -> ProviderDefinition:
        """Return provider metadata or raise a domain error."""

        provider_id = provider.strip().lower()
        definition = PROVIDERS_BY_ID.get(provider_id)

        if definition is None:
            raise UnknownProviderError(
                f"Unknown provider '{provider}'."
            )

        return definition

    @staticmethod
    def _clean_optional_value(value: str | None) -> str | None:
        """Trim an optional string and collapse empty values."""

        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None

    def _resolve_base_url(
        self,
        supplied: str | None,
        current: ProviderCredential | None,
        definition: ProviderDefinition,
    ) -> str | None:
        """Resolve supplied, stored or default provider URL."""

        clean_supplied = self._clean_optional_value(supplied)

        if clean_supplied is not None:
            return clean_supplied.rstrip("/")

        if current is not None and current.base_url:
            return current.base_url.rstrip("/")

        return definition.default_base_url

    @staticmethod
    def _validate_configuration(
        definition: ProviderDefinition,
        key_ciphertext: str | None,
        base_url: str | None,
    ) -> None:
        """Validate the provider configuration before use."""

        if definition.requires_api_key and key_ciphertext is None:
            raise ProviderConfigurationError(
                f"Provider '{definition.provider}' requires an API key."
            )

        if base_url is None:
            raise ProviderConfigurationError(
                f"Provider '{definition.provider}' requires a base URL."
            )

    def _build_state(
        self,
        definition: ProviderDefinition,
        credential: ProviderCredential | None,
    ) -> ProviderState:
        """Build a safe provider response."""

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
            key_trimmed=credential.key_trimmed if credential else None,
            base_url=(
                credential.base_url
                if credential
                else definition.default_base_url
            ),
            model_count=self._model_registry.count_by_provider(
                definition.provider
            ),
        )

    @staticmethod
    def _is_configured(
        definition: ProviderDefinition,
        credential: ProviderCredential | None,
    ) -> bool:
        """Return whether stored data is sufficient to use the provider."""

        if credential is None or not credential.base_url:
            return False

        if definition.requires_api_key:
            return credential.key_ciphertext is not None

        return True
