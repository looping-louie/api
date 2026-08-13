from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field

from src.app.catalogs.models import (
    ModelCapability,
    ModelEndpoint,
    ModelStatus,
)
from src.app.catalogs.providers import ProviderId

from .shared import (
    ListResponse,
    NonEmptyString,
    NonNegativeInteger,
    ResponseSchema,
)


class ModelPricingResponse(ResponseSchema):
    """Token prices for one provider deployment."""

    input_per_million_usd: Decimal = Field(ge=0)
    output_per_million_usd: Decimal = Field(ge=0)
    cached_input_per_million_usd: Decimal | None = Field(
        default=None,
        ge=0,
    )
    valid_until: date | None = None
    note: str | None = None


class ModelDeploymentResponse(ResponseSchema):
    """Provider route configured for a logical model."""

    provider_id: ProviderId
    provider_model_id: NonEmptyString
    endpoint: ModelEndpoint
    context_window: NonNegativeInteger | None = None
    max_output_tokens: NonNegativeInteger | None = None
    pricing: ModelPricingResponse | None = None
    status: ModelStatus
    deprecated_at: date | None = None


class ModelProviderAvailabilityResponse(ResponseSchema):
    """Availability of one provider route for the current workspace."""

    provider_id: ProviderId
    configured: bool
    enabled: bool
    available: bool
    reason: str | None = None


class ModelSummaryResponse(ResponseSchema):
    """Lightweight model returned by the list endpoint."""

    id: str
    name: str
    vendor: str
    family: str
    description: str
    released_at: date
    capabilities: set[ModelCapability]
    status: ModelStatus
    providers: list[ProviderId]
    available: bool
    starting_price: ModelPricingResponse | None = None
    tags: list[str]


class ModelResponse(ResponseSchema):
    """Complete model returned by the describe endpoint."""

    id: str
    name: str
    vendor: str
    family: str
    description: str
    released_at: date
    capabilities: set[ModelCapability]
    status: ModelStatus
    replacement_model_id: str | None = None
    tags: list[str]
    deployments: list[ModelDeploymentResponse]
    availability: list[ModelProviderAvailabilityResponse]
    available: bool


class ModelListResponse(ListResponse[ModelSummaryResponse]):
    """Response returned by GET /models."""
