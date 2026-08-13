"""Workspace-specific model availability calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Mapping, Protocol, Sequence

from src.app.catalogs.models import (
    ModelCapability,
    ModelCatalogEntry,
    ModelDeployment,
    ModelPricing,
    ModelStatus,
)
from src.app.catalogs.providers import ProviderId


class ModelUnavailableReason(StrEnum):
    """Reasons why a model deployment cannot currently be used."""

    MODEL_DEPRECATED = "model_deprecated"
    DEPLOYMENT_DEPRECATED = "deployment_deprecated"
    PROVIDER_NOT_CONFIGURED = "provider_not_configured"
    PROVIDER_DISABLED = "provider_disabled"


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
    released_at: date
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
    released_at: date
    capabilities: frozenset[ModelCapability]
    status: ModelStatus
    replacement_model_id: str | None
    tags: tuple[str, ...]
    deployments: tuple[ModelDeployment, ...]
    availability: tuple[ModelProviderAvailability, ...]
    available: bool


class ProviderStateRepository(Protocol):
    """Persistence contract required by ModelAvailabilityService."""

    async def get_states(
        self,
        *,
        workspace_id: str,
        provider_ids: Sequence[ProviderId],
    ) -> Mapping[ProviderId, ProviderConnectionState]:
        """
        Return workspace-specific provider states indexed by provider ID.

        Providers that have never been configured may be omitted.
        """
        ...


class ModelServiceError(Exception):
    """Base error raised by model services."""


class ModelNotFoundError(ModelServiceError):
    """Raised when a model does not exist in the curated catalog."""

    def __init__(self, *, model_id: str) -> None:
        super().__init__(f"Model '{model_id}' was not found.")
        self.model_id = model_id


class ModelValidationError(ModelServiceError):
    """Raised when model query data is invalid."""

    def __init__(self, *, field_name: str, message: str) -> None:
        super().__init__(f"Invalid model field '{field_name}': {message}")
        self.field_name = field_name
        self.message = message


class ModelAvailabilityService:
    """Calculates model availability for a workspace."""

    def __init__(
        self,
        *,
        provider_state_repository: ProviderStateRepository,
    ) -> None:
        self._provider_state_repository = provider_state_repository

    async def describe(
        self,
        *,
        workspace_id: str,
        model: ModelCatalogEntry,
    ) -> ModelAvailability:
        """Return availability for every deployment of a model."""

        workspace_id = self._require_text(
            workspace_id,
            "workspace_id",
        )
        provider_ids = self._get_provider_ids(model.deployments)

        states = await self._provider_state_repository.get_states(
            workspace_id=workspace_id,
            provider_ids=provider_ids,
        )

        providers = tuple(
            self._evaluate_deployment(
                model=model,
                deployment=deployment,
                provider_state=states.get(deployment.provider_id),
            )
            for deployment in model.deployments
        )

        return ModelAvailability(
            available=any(provider.available for provider in providers),
            providers=providers,
        )

    async def describe_many(
        self,
        *,
        workspace_id: str,
        models: Sequence[ModelCatalogEntry],
    ) -> dict[str, ModelAvailability]:
        """Return availability for several models using one provider lookup."""

        workspace_id = self._require_text(
            workspace_id,
            "workspace_id",
        )
        provider_ids = self._get_provider_ids(
            deployment
            for model in models
            for deployment in model.deployments
        )

        states = await self._provider_state_repository.get_states(
            workspace_id=workspace_id,
            provider_ids=provider_ids,
        )

        results: dict[str, ModelAvailability] = {}

        for model in models:
            providers = tuple(
                self._evaluate_deployment(
                    model=model,
                    deployment=deployment,
                    provider_state=states.get(deployment.provider_id),
                )
                for deployment in model.deployments
            )
            results[model.id] = ModelAvailability(
                available=any(provider.available for provider in providers),
                providers=providers,
            )

        return results

    def _evaluate_deployment(
        self,
        *,
        model: ModelCatalogEntry,
        deployment: ModelDeployment,
        provider_state: ProviderConnectionState | None,
    ) -> ModelProviderAvailability:
        """Evaluate one deployment against its workspace provider state."""

        configured = (
            provider_state.configured
            if provider_state is not None
            else False
        )
        enabled = (
            provider_state.enabled
            if provider_state is not None
            else False
        )
        reason = self._get_unavailable_reason(
            model=model,
            deployment=deployment,
            configured=configured,
            enabled=enabled,
        )

        return ModelProviderAvailability(
            provider_id=deployment.provider_id,
            configured=configured,
            enabled=enabled,
            available=reason is None,
            reason=reason,
        )

    @staticmethod
    def _get_unavailable_reason(
        *,
        model: ModelCatalogEntry,
        deployment: ModelDeployment,
        configured: bool,
        enabled: bool,
    ) -> ModelUnavailableReason | None:
        """Return the first reason that makes a deployment unavailable."""

        if model.status == ModelStatus.DEPRECATED:
            return ModelUnavailableReason.MODEL_DEPRECATED

        if deployment.status == ModelStatus.DEPRECATED:
            return ModelUnavailableReason.DEPLOYMENT_DEPRECATED

        if not configured:
            return ModelUnavailableReason.PROVIDER_NOT_CONFIGURED

        if not enabled:
            return ModelUnavailableReason.PROVIDER_DISABLED

        return None

    @staticmethod
    def _get_provider_ids(
        deployments: Sequence[ModelDeployment] | object,
    ) -> tuple[ProviderId, ...]:
        """Return provider IDs in first-seen order without duplicates."""

        seen: set[ProviderId] = set()
        provider_ids: list[ProviderId] = []

        for deployment in deployments:
            provider_id = deployment.provider_id

            if provider_id in seen:
                continue

            seen.add(provider_id)
            provider_ids.append(provider_id)

        return tuple(provider_ids)

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        """Normalize a required text value."""

        if not isinstance(value, str):
            raise ModelValidationError(
                field_name=field_name,
                message="must be a string",
            )

        normalized = value.strip()

        if not normalized:
            raise ModelValidationError(
                field_name=field_name,
                message="must not be empty",
            )

        return normalized
