"""Domain types used by the curated logical model catalog."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..providers import ProviderId


class ModelCatalogValidationError(ValueError):
    """Raised when curated model definitions are internally inconsistent."""


class ModelStatus(StrEnum):
    """Lifecycle state controlled by the curated catalog."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    PREVIEW = "preview"


class ModelSort(StrEnum):
    """Supported ordering for model catalog queries."""

    ALPHABETICAL_ASC = "alphabetical-asc"
    ALPHABETICAL_DESC = "alphabetical-desc"
    NEWEST = "newest"
    OLDEST = "oldest"


class ModelLab(StrEnum):
    """Organization responsible for developing a catalog model."""

    ANTHROPIC = "anthropic"
    DEEP_COGITO = "deep-cogito"
    DEEPSEEK = "deepseek"
    GOOGLE = "google"
    META = "meta"
    MINIMAX = "minimax"
    MISTRAL = "mistral"
    MOONSHOT = "moonshot"
    NVIDIA = "nvidia"
    OPENAI = "openai"
    QWEN = "qwen"
    THINKING_MACHINES = "thinking-machines"
    Z = "z"


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
class ProviderModelOffering:
    """Provider-specific route for one logical model."""

    model_id: str
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
    lab: ModelLab
    family: str
    description: str
    released_at: date
    capabilities: frozenset[ModelCapability]
    deployments: tuple[ModelDeployment, ...] = field(default_factory=tuple)
    status: ModelStatus = ModelStatus.ACTIVE
    replacement_model_id: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
