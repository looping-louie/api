"""HTTP schemas for static provider and model catalogs."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field

from src.app.catalogs.models import (
    ModelCapability,
    ModelEndpoint,
    ModelStatus,
)
from src.app.catalogs.persona_skills import (
    AgentRole,
    CatalogInstructionCategory,
    SkillArtifact,
    SkillOutput,
    SkillPhase,
)
from src.app.catalogs.providers import ProviderId

from .shared import ListResponse, NonNegativeInteger, ResponseSchema


class CatalogModelPricingResponse(ResponseSchema):
    """Static token prices for one provider-owned offering."""

    input_per_million_usd: Decimal = Field(ge=0)
    output_per_million_usd: Decimal = Field(ge=0)
    cached_input_per_million_usd: Decimal | None = Field(
        default=None,
        ge=0,
    )
    valid_until: date | None = None
    note: str | None = None


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
    offerings: list[CatalogProviderOfferingResponse]


class CatalogProviderOfferingResponse(ResponseSchema):
    """One provider-owned route for a logical model."""

    model_id: str
    provider_model_id: str
    endpoint: ModelEndpoint
    context_window: NonNegativeInteger | None = None
    max_output_tokens: NonNegativeInteger | None = None
    pricing: CatalogModelPricingResponse | None = None
    status: ModelStatus
    deprecated_at: date | None = None


class CatalogInstructionMetadataResponse(ResponseSchema):
    """Static applicability metadata for one built-in instruction."""

    applies_when: list[str]
    applies_to: set[AgentRole]


class CatalogInstructionResponse(ResponseSchema):
    """Fields shared by built-in Persona and Skill catalog definitions."""

    id: str
    name: str
    description: str
    instructions: str
    metadata: CatalogInstructionMetadataResponse
    enabled_by_default: bool
    catalog_version: NonNegativeInteger
    deprecated: bool
    category: CatalogInstructionCategory | None


class CatalogPersonaResponse(CatalogInstructionResponse):
    """Static built-in Persona definition."""

    skill_ids: list[str]
    default_for: set[AgentRole]


class CatalogSkillStrictnessResponse(ResponseSchema):
    """Default review strictness for one built-in Skill."""

    prototype: NonNegativeInteger
    mvp: NonNegativeInteger
    production: NonNegativeInteger


class CatalogSkillResponse(CatalogInstructionResponse):
    """Static built-in Skill definition."""

    reviewer_default_strictness: CatalogSkillStrictnessResponse | None
    phase: SkillPhase | None
    artifacts: list[SkillArtifact]
    output: SkillOutput | None
