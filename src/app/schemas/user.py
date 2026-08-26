"""HTTP schemas for the current API user profile."""

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from src.app.schemas.execution import HarnessRequest, HarnessResponse
from src.app.schemas.shared import NonEmptyString, RequestSchema, ResponseSchema


class ConfiguredModelAvailabilityRequest(RequestSchema):
    """One explicit User availability policy for a logical model."""

    id: NonEmptyString
    status: Literal['enabled', 'disabled']


class ConfiguredModelAvailabilityResponse(ResponseSchema):
    """One persisted User availability policy for a logical model."""

    id: str
    status: Literal['enabled', 'disabled']


class UserSettingsRequest(RequestSchema):
    """Mutable user-level execution defaults."""

    default_model_id: NonEmptyString | None = None
    default_harness: HarnessRequest | None = None
    default_model_availability: Literal['enabled', 'disabled'] = 'enabled'
    configured_models: list[ConfiguredModelAvailabilityRequest] = Field(
        default_factory=list,
    )

    @model_validator(mode='after')
    def require_unique_configured_models(self) -> 'UserSettingsRequest':
        """Reject duplicate model overrides that would produce ambiguous policy."""

        model_ids = [model.id for model in self.configured_models]
        if len(model_ids) != len(set(model_ids)):
            raise ValueError('configured_models must not contain duplicate IDs.')
        return self


class UserSettingsResponse(ResponseSchema):
    """Persisted user-level execution defaults."""

    default_model_id: str | None
    default_harness: HarnessResponse | None
    default_model_availability: Literal['enabled', 'disabled']
    configured_models: list[ConfiguredModelAvailabilityResponse]


class UserResponse(ResponseSchema):
    """Durable representation of a request identity."""

    id: str
    created_at: datetime
    updated_at: datetime
    settings: UserSettingsResponse
