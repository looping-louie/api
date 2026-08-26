"""Workspace-specific model availability calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Sequence

from src.app.catalogs.models import (
    ModelCapability,
    ModelCatalogEntry,
    ModelEndpoint,
    ModelOffering,
    ModelPricing,
    ModelStatus,
)
from src.app.catalogs.providers import ProviderId
from src.app.repositories.linked_services import LinkedServiceRepository


class ModelUnavailableReason(StrEnum):
    """Reasons why a model deployment cannot currently be used."""

    MODEL_DEPRECATED = "model_deprecated"
    DEPLOYMENT_DEPRECATED = "deployment_deprecated"
    MODEL_DISABLED = "model_disabled"
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
class ModelOfferingAvailability:
    """Provider offering joined with workspace availability state."""

    provider_id: ProviderId
    provider_model_id: str
    endpoint: ModelEndpoint
    context_window: int | None
    max_output_tokens: int | None
    pricing: ModelPricing | None
    status: ModelStatus
    deprecated_at: date | None
    configured: bool
    enabled: bool
    available: bool
    reason: ModelUnavailableReason | None = None


@dataclass(frozen=True, slots=True)
class ModelAvailability:
    """Aggregated availability information for one logical model."""

    available: bool
    offerings: tuple[ModelOfferingAvailability, ...]


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
    available: bool
    offerings: tuple[ModelOfferingAvailability, ...]
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
    offerings: tuple[ModelOfferingAvailability, ...]
    available: bool


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
        linked_service_repository: LinkedServiceRepository,
    ) -> None:
        self._linked_service_repository = linked_service_repository

    async def describe(
        self,
        *,
        workspace_id: str,
        model: ModelCatalogEntry,
        offerings: Sequence[ModelOffering],
        model_enabled: bool = True,
    ) -> ModelAvailability:
        """Return availability for every provider offering of a model."""

        workspace_id = self._require_text(
            workspace_id,
            "workspace_id",
        )
        provider_ids = self._get_provider_ids(offerings)

        states = await self._get_provider_states(
            workspace_id=workspace_id,
            provider_ids=provider_ids,
        )

        evaluated_offerings = tuple(
            self._evaluate_offering(
                model=model,
                offering=offering,
                provider_state=states.get(offering.provider_id),
                model_enabled=model_enabled,
            )
            for offering in offerings
        )

        return ModelAvailability(
            available=any(offering.available for offering in evaluated_offerings),
            offerings=evaluated_offerings,
        )

    async def describe_many(
        self,
        *,
        workspace_id: str,
        models: Sequence[ModelCatalogEntry],
        offerings_by_model: dict[str, Sequence[ModelOffering]],
        model_enabled_by_id: dict[str, bool] | None = None,
    ) -> dict[str, ModelAvailability]:
        """Return availability for several models using one provider lookup."""

        workspace_id = self._require_text(
            workspace_id,
            "workspace_id",
        )
        provider_ids = self._get_provider_ids(
            offering
            for model in models
            for offering in offerings_by_model[model.id]
        )

        states = await self._get_provider_states(
            workspace_id=workspace_id,
            provider_ids=provider_ids,
        )

        results: dict[str, ModelAvailability] = {}

        for model in models:
            offerings = tuple(
                self._evaluate_offering(
                    model=model,
                    offering=offering,
                    provider_state=states.get(offering.provider_id),
                    model_enabled=(
                        model_enabled_by_id.get(model.id, True)
                        if model_enabled_by_id is not None
                        else True
                    ),
                )
                for offering in offerings_by_model[model.id]
            )
            results[model.id] = ModelAvailability(
                available=any(offering.available for offering in offerings),
                offerings=offerings,
            )

        return results

    async def _get_provider_states(
        self,
        *,
        workspace_id: str,
        provider_ids: Sequence[ProviderId],
    ) -> dict[ProviderId, ProviderConnectionState]:
        """Aggregate configured workspace services by catalog provider type."""

        requested_provider_ids = set(provider_ids)
        states: dict[ProviderId, ProviderConnectionState] = {}
        for linked_service in await self._linked_service_repository.list_for_workspace_owner(
            workspace_id
        ):
            try:
                provider_id = ProviderId(linked_service.provider_type)
            except ValueError:
                continue
            if provider_id not in requested_provider_ids:
                continue
            configured = linked_service.base_url is not None
            existing = states.get(provider_id)
            states[provider_id] = ProviderConnectionState(
                provider_id=provider_id,
                configured=(existing.configured if existing is not None else False)
                or configured,
                enabled=(existing.enabled if existing is not None else False)
                or (configured and linked_service.enabled),
            )
        return states

    def _evaluate_offering(
        self,
        *,
        model: ModelCatalogEntry,
        offering: ModelOffering,
        provider_state: ProviderConnectionState | None,
        model_enabled: bool,
    ) -> ModelOfferingAvailability:
        """Evaluate one provider offering against its workspace state."""

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
            offering=offering,
            model_enabled=model_enabled,
            configured=configured,
            enabled=enabled,
        )

        return ModelOfferingAvailability(
            provider_id=offering.provider_id,
            provider_model_id=offering.provider_model_id,
            endpoint=offering.endpoint,
            context_window=offering.context_window,
            max_output_tokens=offering.max_output_tokens,
            pricing=offering.pricing,
            status=offering.status,
            deprecated_at=offering.deprecated_at,
            configured=configured,
            enabled=enabled,
            available=reason is None,
            reason=reason,
        )

    @staticmethod
    def _get_unavailable_reason(
        *,
        model: ModelCatalogEntry,
        offering: ModelOffering,
        model_enabled: bool,
        configured: bool,
        enabled: bool,
    ) -> ModelUnavailableReason | None:
        """Return the first reason that makes a provider offering unavailable."""

        if model.status == ModelStatus.DEPRECATED:
            return ModelUnavailableReason.MODEL_DEPRECATED

        if offering.status == ModelStatus.DEPRECATED:
            return ModelUnavailableReason.DEPLOYMENT_DEPRECATED

        if not model_enabled:
            return ModelUnavailableReason.MODEL_DISABLED

        if not configured:
            return ModelUnavailableReason.PROVIDER_NOT_CONFIGURED

        if not enabled:
            return ModelUnavailableReason.PROVIDER_DISABLED

        return None

    @staticmethod
    def _get_provider_ids(
        offerings: Sequence[ModelOffering] | object,
    ) -> tuple[ProviderId, ...]:
        """Return provider IDs in first-seen order without duplicates."""

        seen: set[ProviderId] = set()
        provider_ids: list[ProviderId] = []

        for offering in offerings:
            provider_id = offering.provider_id

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
