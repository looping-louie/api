"""Internal domain models for model provider configuration."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RequestActor:
    """Organisation and user associated with the current request."""

    org_id: str
    user_id: str


@dataclass(frozen=True)
class ProviderDefinition:
    """Static metadata for one supported model provider."""

    provider: str
    name: str
    description: str
    logo_url: str
    requires_api_key: bool
    default_base_url: str | None


@dataclass
class ProviderCredential:
    """Encrypted provider configuration persisted by the repository."""

    id: str
    org_id: str
    provider: str
    enabled: bool
    enabled_by: str | None
    enabled_on: datetime | None
    key_trimmed: str | None
    key_ciphertext: str | None
    key_version: int
    base_url: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ProviderState:
    """Safe provider representation returned to API consumers."""

    provider: str
    name: str
    description: str
    logo_url: str
    requires_api_key: bool
    configured: bool
    enabled: bool
    key_trimmed: str | None
    base_url: str | None
    model_count: int


@dataclass(frozen=True)
class ProviderTestResult:
    """Result of testing one provider configuration."""

    provider: str
    success: bool
    message: str
    latency_ms: int
