"""HTTP schemas for workspace-owned linked services."""

from datetime import datetime

from pydantic import Field, StrictBool, model_validator

from src.app.catalogs.providers import ProviderId

from .shared import RequestSchema, ResourceName, ResponseSchema


class LinkedServiceConfigRequest(RequestSchema):
    """Type-specific provider settings accepted for a linked service."""

    api_key: str | None = Field(
        default=None,
        min_length=1,
        description='Provider API key. Null clears the stored key on update.',
    )
    base_url: str | None = Field(
        default=None,
        min_length=1,
        description='Provider API base URL. Null restores the provider default.',
    )


class LinkedServiceCreateRequest(RequestSchema):
    """Fields required to create a workspace linked service."""

    name: ResourceName
    provider_type: ProviderId
    enabled: StrictBool = True
    config: LinkedServiceConfigRequest = Field(
        default_factory=LinkedServiceConfigRequest,
    )


class LinkedServicePatchRequest(RequestSchema):
    """Mutable fields of a workspace linked service."""

    name: ResourceName | None = None
    enabled: StrictBool | None = None
    config: LinkedServiceConfigRequest | None = None

    @model_validator(mode='after')
    def require_update(self) -> 'LinkedServicePatchRequest':
        """Require at least one mutable field to be explicitly supplied."""
        if not self.model_fields_set:
            raise ValueError('At least one linked service field must be updated.')
        if 'enabled' in self.model_fields_set and self.enabled is None:
            raise ValueError('Enabled must be true or false.')
        return self


class LinkedServiceConfigResponse(ResponseSchema):
    """Safe configuration values returned for a linked service."""

    base_url: str | None
    key_trimmed: str | None
    configured: bool
    available_models: list[str]


class LinkedServiceResponse(ResponseSchema):
    """Workspace-owned linked service returned by the REST API."""

    id: str
    name: str
    provider_type: str
    enabled: bool
    config: LinkedServiceConfigResponse
    version: int = Field(gt=0)
    created_at: datetime
    updated_at: datetime
