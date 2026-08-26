"""Application service for querying the curated model catalog."""

from __future__ import annotations

from typing import Sequence

from src.app.catalogs.models import (
    CATALOG_INDEX,
    CatalogIndex,
    MODEL_CATALOG,
    ModelCapability,
    ModelCatalogEntry,
    ModelLab,
    ModelOffering,
    ModelSort,
    ModelStatus,
)
from src.app.catalogs.providers import ProviderId
from src.app.services.models.availability import (
    ModelAvailability,
    ModelAvailabilityService,
    ModelDocument,
    ModelNotFoundError,
    ModelSummary,
    ModelValidationError,
)
from src.app.services.shared.tenant import TenantService
from src.app.models.user import UserSettings
from src.app.services.users import UserService


class ModelCatalogService:
    """Application service for querying the curated model catalog."""

    def __init__(
        self,
        *,
        tenant_service: TenantService,
        user_service: UserService | None = None,
        availability_service: ModelAvailabilityService,
        catalog: Sequence[ModelCatalogEntry] = MODEL_CATALOG,
        catalog_index: CatalogIndex = CATALOG_INDEX,
    ) -> None:
        """Store model catalog dependencies."""

        self._tenant_service = tenant_service
        self._user_service = user_service
        self._availability_service = availability_service
        self._catalog = tuple(catalog)
        self._catalog_index = catalog_index
        self._catalog_by_id = {
            model.id: model
            for model in self._catalog
        }

    async def list(
        self,
        *,
        user_id: str,
        workspace_id: str,
        provider_id: ProviderId | None = None,
        capability: ModelCapability | None = None,
        model_status: ModelStatus | None = None,
        labs: Sequence[ModelLab] = (),
        sort: ModelSort | None = None,
        available: bool | None = None,
        search: str | None = None,
        include_deprecated: bool = False,
    ) -> list[ModelSummary]:
        """List curated models and their workspace availability."""

        await self._require_workspace_access(
            user_id=user_id,
            workspace_id=workspace_id,
        )
        settings = await self._user_settings(user_id=user_id)
        normalized_search = self._normalize_search(search)
        selected_labs = frozenset(labs)

        models = [
            model
            for model in self._catalog
            if self._matches_static_filters(
                model=model,
                provider_id=provider_id,
                capability=capability,
                model_status=model_status,
                labs=selected_labs,
                search=normalized_search,
                include_deprecated=include_deprecated,
            )
        ]

        availability_by_model = await self._availability_service.describe_many(
            workspace_id=workspace_id,
            models=models,
            offerings_by_model={
                model.id: self.offerings_for_model(model)
                for model in models
            },
            model_enabled_by_id={
                model.id: self._model_enabled(model.id, settings)
                for model in models
            },
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

        if sort is not None:
            summaries = self._sort_summaries(summaries, sort)

        return summaries

    async def describe(
        self,
        *,
        user_id: str,
        model_id: str,
        workspace_id: str,
    ) -> ModelDocument:
        """Return a complete model and its workspace availability."""

        await self._require_workspace_access(
            user_id=user_id,
            workspace_id=workspace_id,
        )
        settings = await self._user_settings(user_id=user_id)
        model = self.require_model(model_id)

        availability = await self._availability_service.describe(
            workspace_id=workspace_id,
            model=model,
            offerings=self.offerings_for_model(model),
            model_enabled=self._model_enabled(model.id, settings),
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

    @staticmethod
    def _model_enabled(model_id: str, settings: object) -> bool:
        """Return the configured model state or the User default policy."""

        for configured_model in getattr(settings, 'configured_models'):
            if configured_model.id == model_id:
                return configured_model.status == 'enabled'
        return getattr(settings, 'default_model_availability') == 'enabled'

    async def _user_settings(self, *, user_id: str) -> UserSettings:
        """Return the User policy or the enabled default for catalog-only callers."""

        if self._user_service is None:
            return UserSettings()
        return (await self._user_service.get(user_id=user_id)).settings

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
        labs: frozenset[ModelLab],
        search: str | None,
        include_deprecated: bool,
    ) -> bool:
        """Return whether a model satisfies filters independent of workspace."""

        if (
            model_status is None
            and not include_deprecated
            and model.status == ModelStatus.DEPRECATED
        ):
            return False

        if model_status is not None and model.status != model_status:
            return False

        if labs and model.lab not in labs:
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

    def _has_provider(
        self,
        model: ModelCatalogEntry,
        provider_id: ProviderId,
    ) -> bool:
        """Return whether the model has a deployment for a provider."""

        return any(
            offering.provider_id == provider_id
            for offering in self.offerings_for_model(model)
        )

    @staticmethod
    def _matches_search(
        model: ModelCatalogEntry,
        search: str,
    ) -> bool:
        """Return whether searchable model fields contain a query."""

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
        """Build a list representation from catalog and availability data."""

        return ModelSummary(
            id=model.id,
            name=model.name,
            vendor=model.vendor,
            family=model.family,
            description=model.description,
            released_at=model.released_at,
            capabilities=model.capabilities,
            status=model.status,
            available=availability.available,
            offerings=availability.offerings,
            tags=model.tags,
        )

    def _to_document(
        self,
        *,
        model: ModelCatalogEntry,
        availability: ModelAvailability,
    ) -> ModelDocument:
        """Build a detailed representation from catalog and availability."""

        return ModelDocument(
            id=model.id,
            name=model.name,
            vendor=model.vendor,
            family=model.family,
            description=model.description,
            released_at=model.released_at,
            capabilities=model.capabilities,
            status=model.status,
            replacement_model_id=model.replacement_model_id,
            tags=model.tags,
            offerings=availability.offerings,
            available=availability.available,
        )

    def offerings_for_model(
        self,
        model: ModelCatalogEntry,
    ) -> tuple[ModelOffering, ...]:
        """Return provider-owned offerings for one logical model."""

        return self._catalog_index.offerings_for_model(model.id)

    async def _require_workspace_access(
        self,
        *,
        user_id: str,
        workspace_id: str,
    ) -> None:
        """Require access to the Workspace addressed by the model route."""

        await self._tenant_service.require_access(
            user_id=user_id,
            workspace_id=workspace_id,
        )

    @staticmethod
    def _normalize_search(search: str | None) -> str | None:
        """Normalize an optional case-insensitive search query."""

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
    def _sort_summaries(
        summaries: list[ModelSummary],
        sort: ModelSort,
    ) -> list[ModelSummary]:
        """Return model summaries ordered by the requested catalog sort."""

        if sort == ModelSort.ALPHABETICAL_DESC:
            return sorted(
                summaries,
                key=lambda model: (model.name.casefold(), model.id),
                reverse=True,
            )

        if sort == ModelSort.NEWEST:
            return sorted(
                summaries,
                key=lambda model: (
                    -model.released_at.toordinal(),
                    model.name.casefold(),
                    model.id,
                ),
            )

        if sort == ModelSort.OLDEST:
            return sorted(
                summaries,
                key=lambda model: (
                    model.released_at,
                    model.name.casefold(),
                    model.id,
                ),
            )

        return sorted(
            summaries,
            key=lambda model: (model.name.casefold(), model.id),
        )

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
