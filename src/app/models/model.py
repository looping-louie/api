"""Domain projections for model availability and catalog queries."""

from dataclasses import dataclass
from enum import StrEnum

from src.app.catalogs.models import (
    ModelCapability,
    ModelDeployment,
    ModelPricing,
    ModelStatus,
)
from src.app.catalogs.providers import ProviderId


class ModelUnavailableReason(StrEnum):
    """Reasons why a model deployment cannot currently be used."""

    MODEL_DEPRECATED = 'model_deprecated'
    DEPLOYMENT_DEPRECATED = 'deployment_deprecated'
    PROVIDER_NOT_CONFIGURED = 'provider_not_configured'
    PROVIDER_DISABLED = 'provider_disabled'


@dataclass(frozen=True, slots=True)
class ProviderConnectionState:
    """Workspace-specific configuration state for one provider."""

    provider_id: ProviderId
    configured: bool
    enabled: bool


@dataclass(frozen=True, slots=True)
class ModelProviderAvailability:
    """Availability of one provider deployment."""

    provider_id: ProviderId
    configured: bool
    enabled: bool
    available: bool
    reason: ModelUnavailableReason | None = None


@dataclass(frozen=True, slots=True)
class ModelAvailability:
    """Aggregated availability information for one logical model."""

    available: bool
    providers: tuple[ModelProviderAvailability, ...]


@dataclass(frozen=True, slots=True)
class ModelSummary:
    """Lightweight model representation returned by list operations."""

    id: str
    name: str
    vendor: str
    family: str
    description: str
    capabilities: frozenset[ModelCapability]
    status: ModelStatus
    providers: tuple[ProviderId, ...]
    available: bool
    starting_price: ModelPricing | None
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ModelDocument:
    """Complete model representation returned by describe operations."""

    id: str
    name: str
    vendor: str
    family: str
    description: str
    capabilities: frozenset[ModelCapability]
    status: ModelStatus
    replacement_model_id: str | None
    tags: tuple[str, ...]
    deployments: tuple[ModelDeployment, ...]
    availability: tuple[ModelProviderAvailability, ...]
    available: bool
