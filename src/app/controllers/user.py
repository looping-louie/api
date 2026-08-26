"""HTTP controller for current API user profiles."""

from typing import Sequence

from src.app.catalogs.models import ModelCapability, ModelLab, ModelSort, ModelStatus
from src.app.catalogs.providers import ProviderId
from src.app.models.user import ConfiguredModelAvailability, UserDocument
from src.app.models.pipeline import PipelineHarness
from src.app.schemas.model import ModelListResponse, ModelResponse, ModelSummaryResponse
from src.app.schemas.user import UserResponse, UserSettingsRequest, UserSettingsResponse
from src.app.services.models.catalog import ModelCatalogService
from src.app.services.users import UserService


class UserController:
    """Translate current-user HTTP operations into service calls."""

    def __init__(self, *, service: UserService) -> None:
        """Store the user application service."""

        self._service = service

    async def get_current(self, *, user_id: str) -> UserResponse:
        """Return the durable profile for the request identity."""

        return self._response(await self._service.get(user_id=user_id))

    async def register_current(self, *, user_id: str) -> UserResponse:
        """Ensure that the request identity has a durable profile."""

        return self._response(await self._service.register(user_id=user_id))

    async def update_current_settings(
        self,
        *,
        user_id: str,
        settings: UserSettingsRequest,
    ) -> UserResponse:
        """Replace execution settings for the current user."""

        harness = settings.default_harness
        return self._response(await self._service.update_settings(
            user_id=user_id,
            default_model_id=settings.default_model_id,
            default_harness=(
                PipelineHarness(
                    kind=harness.kind,
                    version=harness.version,
                    config=harness.config,
                )
                if harness is not None
                else None
            ),
            default_model_availability=settings.default_model_availability,
            configured_models=tuple(
                ConfiguredModelAvailability(id=model.id, status=model.status)
                for model in settings.configured_models
            ),
        ))

    @staticmethod
    def _response(document: UserDocument) -> UserResponse:
        """Map a user document to its public representation."""

        return UserResponse(
            id=document.id,
            created_at=document.created_at,
            updated_at=document.updated_at,
            settings=UserSettingsResponse(
                default_model_id=document.settings.default_model_id,
                default_harness=(
                    {
                        'kind': document.settings.default_harness.kind,
                        'version': document.settings.default_harness.version,
                        'config': document.settings.default_harness.config,
                    }
                    if document.settings.default_harness is not None
                    else None
                ),
                default_model_availability=document.settings.default_model_availability,
                configured_models=[
                    {
                        'id': model.id,
                        'status': model.status,
                    }
                    for model in document.settings.configured_models
                ],
            ),
        )


class UserModelController:
    """Translate current-User model catalog HTTP operations."""

    def __init__(self, *, model_catalog_service: ModelCatalogService) -> None:
        """Store the User-scoped model catalog service."""

        self._model_catalog_service = model_catalog_service

    async def list(
        self,
        *,
        user_id: str,
        provider_id: ProviderId | None = None,
        capability: ModelCapability | None = None,
        model_status: ModelStatus | None = None,
        labs: Sequence[ModelLab] = (),
        sort: ModelSort | None = None,
        offset: int = 0,
        available: bool | None = None,
        search: str | None = None,
        include_deprecated: bool = False,
    ) -> ModelListResponse:
        """List curated models and availability for the current User."""

        models = await self._model_catalog_service.list(
            user_id=user_id,
            provider_id=provider_id,
            capability=capability,
            model_status=model_status,
            labs=labs,
            sort=sort,
            available=available,
            search=search,
            include_deprecated=include_deprecated,
        )
        page = models[offset : offset + 24]
        return ModelListResponse(
            items=[ModelSummaryResponse.model_validate(model) for model in page],
            total=len(models),
        )

    async def describe(self, *, user_id: str, model_id: str) -> ModelResponse:
        """Describe one model and its availability for the current User."""

        model = await self._model_catalog_service.describe(
            user_id=user_id,
            model_id=model_id,
        )
        return ModelResponse.model_validate(model)
