"""HTTP schemas for model provider configuration."""

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator


class ProviderPatchRequest(BaseModel):
    """Fields that may change in a workspace provider configuration."""

    api_key: str | None = Field(
        default=None,
        min_length=1,
        description="Provider API key. Null clears the stored key.",
    )
    base_url: str | None = Field(
        default=None,
        min_length=1,
        description="Custom API base URL. Null restores the catalog default.",
    )
    enabled: StrictBool | None = Field(
        default=None,
        description="Whether models from this provider are available.",
    )

    @model_validator(mode="after")
    def require_update(self) -> "ProviderPatchRequest":
        """Require a meaningful update with a concrete enabled value."""

        if not self.model_fields_set:
            raise ValueError("At least one provider field must be updated.")
        if "enabled" in self.model_fields_set and self.enabled is None:
            raise ValueError("Enabled must be true or false.")

        return self


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
    model_catalog_note: str | None
