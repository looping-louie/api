"""HTTP schemas for static provider and model catalogs."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field

from src.app.catalogs.models import (
    ModelCapability,
    ModelStatus,
)
from src.app.catalogs.providers import ProviderId

from .shared import ListResponse, NonNegativeInteger, ResponseSchema


class CatalogModelPricingResponse(ResponseSchema):
    """Static token prices for one model deployment."""

    input_per_million_usd: Decimal = Field(ge=0)
    output_per_million_usd: Decimal = Field(ge=0)


class CatalogModelSummaryResponse(ResponseSchema):
    """Static model metadata returned by the catalog list endpoint."""

    id: str
    name: str
    vendor: str
    family: str
    description: str
    released_at: date
    capabilities: set[ModelCapability]
    status: ModelStatus
    provider_ids: list[ProviderId]
    deployment_count: NonNegativeInteger
    starting_price: CatalogModelPricingResponse | None = None
    tags: list[str]


class CatalogModelListResponse(ListResponse[CatalogModelSummaryResponse]):
    """Response returned by the static model catalog endpoint."""


class CatalogProviderResponse(ResponseSchema):
    """Static metadata for one supported provider type."""

    id: ProviderId
    name: str
    description: str
    logo_url: str
    requires_api_key: bool
    default_base_url: str | None
    model_catalog_note: str | None = None