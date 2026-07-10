"""HTTP schemas for model provider configuration."""

from pydantic import BaseModel, ConfigDict, Field


class ProviderSetRequest(BaseModel):
    """Request payload for creating or replacing provider configuration."""

    api_key: str | None = Field(
        default=None,
        min_length=1,
        description="Provider API key. Optional for Ollama.",
    )
    base_url: str | None = Field(
        default=None,
        min_length=1,
        description="Custom API base URL.",
    )


class ProviderEnabledRequest(BaseModel):
    """Request payload for enabling or disabling a provider."""

    enabled: bool


class ProviderResponse(BaseModel):
    """Safe provider configuration returned to API consumers."""

    model_config = ConfigDict(from_attributes=True)

    provider: str
    name: str
    description: str
    logo_url: str
    requires_api_key: bool
    configured: bool
    enabled: bool
    key_trimmed: str | None
    base_url: str | None
    model_count: int = Field(ge=0)


class ProviderTestResponse(BaseModel):
    """Result returned after testing a provider connection."""

    model_config = ConfigDict(from_attributes=True)

    provider: str
    success: bool
    message: str
    latency_ms: int = Field(ge=0)
