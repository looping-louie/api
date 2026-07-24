"""Internal domain models for model provider configuration."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RequestActor:
    """Organisation and user associated with the current request."""

    workspace_id: str
    user_id: str


@dataclass
class ProviderCredential:
    """Encrypted provider configuration persisted by the repository."""

    id: str
    workspace_id: str
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
    model_catalog_note: str | None
