"""Domain types used by the curated logical model catalog."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum

from ..providers import ProviderId


class ModelCatalogValidationError(ValueError):
    """Raised when curated model definitions are internally inconsistent."""


class ModelStatus(StrEnum):
    """Lifecycle state controlled by the curated catalog."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    PREVIEW = "preview"


class ModelEndpoint(StrEnum):
    """Provider API used to invoke a model deployment."""

    CHAT_COMPLETIONS = "chat_completions"
    MESSAGES = "messages"
    RESPONSES = "responses"


class ModelCapability(StrEnum):
    """Capabilities relevant to Looping Louie workflows."""

    CODING = "coding"
    FUNCTION_CALLING = "function_calling"
    REASONING = "reasoning"
    STRUCTURED_OUTPUT = "structured_output"
    TEXT = "text"
    VISION = "vision"


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """Token prices for one provider deployment."""

    input_per_million_usd: Decimal
    output_per_million_usd: Decimal
    cached_input_per_million_usd: Decimal | None = None
    valid_until: date | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class ModelDeployment:
    """Provider-specific route through which a logical model is invoked."""

    provider_id: ProviderId
    provider_model_id: str
    endpoint: ModelEndpoint
    context_window: int | None = None
    max_output_tokens: int | None = None
    pricing: ModelPricing | None = None
    status: ModelStatus = ModelStatus.ACTIVE
    deprecated_at: date | None = None


@dataclass(frozen=True, slots=True)
class ModelCatalogEntry:
    """Provider-independent model exposed by Looping Louie."""

    id: str
    name: str
    vendor: str
    family: str
    description: str
    capabilities: frozenset[ModelCapability]
    deployments: tuple[ModelDeployment, ...]
    status: ModelStatus = ModelStatus.ACTIVE
    replacement_model_id: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
