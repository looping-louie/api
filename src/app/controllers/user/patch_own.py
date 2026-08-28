"""Controller for updating current User settings."""

from src.app.models.pipeline import PipelineHarness
from src.app.models.user import ConfiguredModelAvailability
from src.app.schemas.user import UserResponse, UserSettingsRequest
from src.app.services.users import UserService

from .response import user_response


class UserPatchOwnController:
    """Update the current User's execution settings."""

    async def update_current_settings(
        self,
        *,
        user_id: str,
        settings: UserSettingsRequest,
    ) -> UserResponse:
        """Replace execution settings for the current User."""

        harness = settings.default_harness
        return user_response(await self._user_service.update_settings(
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

    _user_service: UserService