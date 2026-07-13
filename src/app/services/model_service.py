from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping, Protocol, Sequence

from src.app.catalogs.models import (
    MODEL_CATALOG,
    MODEL_CATALOG_BY_ID,
    ModelCapability,
    ModelCatalogEntry,
    ModelDeployment,
    ModelPricing,
    ModelStatus,
    ProviderId,
)
from src.app.services.shared.tenant_service import TenantService


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


class ModelCatalogService:
    """Application service for querying the curated model catalog."""

    def __init__(
        self,
        *,
        tenant_service: TenantService,
        availability_service: ModelAvailabilityService,
        catalog: Sequence[ModelCatalogEntry] = MODEL_CATALOG,
    ) -> None:
        self._tenant_service = tenant_service
        self._availability_service = availability_service
        self._catalog = tuple(catalog)
        self._catalog_by_id = {
            model.id: model
            for model in self._catalog
        }

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
        provider_id: ProviderId | None = None,
        capability: ModelCapability | None = None,
        model_status: ModelStatus | None = None,
        available: bool | None = None,
        search: str | None = None,
        include_deprecated: bool = False,
    ) -> list[ModelSummary]:
        """List curated models and their workspace availability."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        normalized_search = self._normalize_search(search)

        models = [
            model
            for model in self._catalog
            if self._matches_static_filters(
                model=model,
                provider_id=provider_id,
                capability=capability,
                model_status=model_status,
                search=normalized_search,
                include_deprecated=include_deprecated,
            )
        ]

        availability_by_model = await self._availability_service.describe_many(
            workspace_id=workspace_id,
            models=models,
        )

        summaries = [
            self._to_summary(
                model=model,
                availability=availability_by_model[model.id],
            )
            for model in models
        ]

        if available is not None:
            summaries = [
                summary
                for summary in summaries
                if summary.available is available
            ]

        return summaries

    async def describe(
        self,
        *,
        user_id: str,
        model_id: str,
        requested_workspace_id: str | None = None,
    ) -> ModelDocument:
        """Return a complete model and its workspace availability."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        model = self.require_model(model_id)

        availability = await self._availability_service.describe(
            workspace_id=workspace_id,
            model=model,
        )

        return self._to_document(
            model=model,
            availability=availability,
        )

    def require_model(self, model_id: str) -> ModelCatalogEntry:
        """Return one catalog entry or raise ModelNotFoundError."""

        normalized_model_id = self._require_text(
            model_id,
            "model_id",
        )
        model = self._catalog_by_id.get(normalized_model_id)

        if model is None:
            raise ModelNotFoundError(
                model_id=normalized_model_id,
            )

        return model

    def get_many(
        self,
        *,
        model_ids: Sequence[str],
    ) -> dict[str, ModelCatalogEntry]:
        """
        Return existing catalog entries indexed by model ID.

        Missing models are omitted so this method can later back
        ReferenceResolver.
        """

        result: dict[str, ModelCatalogEntry] = {}

        for model_id in model_ids:
            normalized_model_id = self._require_text(
                model_id,
                "model_id",
            )
            model = self._catalog_by_id.get(normalized_model_id)

            if model is not None:
                result[normalized_model_id] = model

        return result

    def _matches_static_filters(
        self,
        *,
        model: ModelCatalogEntry,
        provider_id: ProviderId | None,
        capability: ModelCapability | None,
        model_status: ModelStatus | None,
        search: str | None,
        include_deprecated: bool,
    ) -> bool:
        if not include_deprecated and model.status == ModelStatus.DEPRECATED:
            return False

        if model_status is not None and model.status != model_status:
            return False

        if capability is not None and capability not in model.capabilities:
            return False

        if provider_id is not None and not self._has_provider(
            model,
            provider_id,
        ):
            return False

        if search is not None and not self._matches_search(
            model,
            search,
        ):
            return False

        return True

    @staticmethod
    def _has_provider(
        model: ModelCatalogEntry,
        provider_id: ProviderId,
    ) -> bool:
        return any(
            deployment.provider_id == provider_id
            for deployment in model.deployments
        )

    @staticmethod
    def _matches_search(
        model: ModelCatalogEntry,
        search: str,
    ) -> bool:
        searchable_values = (
            model.id,
            model.name,
            model.vendor,
            model.family,
            model.description,
            *model.tags,
        )

        return any(
            search in value.casefold()
            for value in searchable_values
        )

    def _to_summary(
        self,
        *,
        model: ModelCatalogEntry,
        availability: ModelAvailability,
    ) -> ModelSummary:
        return ModelSummary(
            id=model.id,
            name=model.name,
            vendor=model.vendor,
            family=model.family,
            description=model.description,
            capabilities=model.capabilities,
            status=model.status,
            providers=self._get_model_providers(model),
            available=availability.available,
            starting_price=self._get_starting_price(model),
            tags=model.tags,
        )

    @staticmethod
    def _to_document(
        *,
        model: ModelCatalogEntry,
        availability: ModelAvailability,
    ) -> ModelDocument:
        return ModelDocument(
            id=model.id,
            name=model.name,
            vendor=model.vendor,
            family=model.family,
            description=model.description,
            capabilities=model.capabilities,
            status=model.status,
            replacement_model_id=model.replacement_model_id,
            tags=model.tags,
            deployments=model.deployments,
            availability=availability.providers,
            available=availability.available,
        )

    @staticmethod
    def _get_model_providers(
        model: ModelCatalogEntry,
    ) -> tuple[ProviderId, ...]:
        providers: list[ProviderId] = []
        seen: set[ProviderId] = set()

        for deployment in model.deployments:
            if deployment.provider_id in seen:
                continue

            seen.add(deployment.provider_id)
            providers.append(deployment.provider_id)

        return tuple(providers)

    @staticmethod
    def _get_starting_price(
        model: ModelCatalogEntry,
    ) -> ModelPricing | None:
        prices = [
            deployment.pricing
            for deployment in model.deployments
            if deployment.status != ModelStatus.DEPRECATED
            and deployment.pricing is not None
        ]

        if not prices:
            return None

        return min(
            prices,
            key=lambda price: (
                price.input_per_million_usd
                + price.output_per_million_usd
            ),
        )

    async def _resolve_workspace_id(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None,
    ) -> str:
        tenant = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return tenant.workspace_id

    @staticmethod
    def _normalize_search(search: str | None) -> str | None:
        if search is None:
            return None

        if not isinstance(search, str):
            raise ModelValidationError(
                field_name="search",
                message="must be a string",
            )

        normalized = search.strip().casefold()
        return normalized or None

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
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
