"""HTTP controller for current API user profiles."""

from src.app.models.user import UserDocument
from src.app.models.pipeline import PipelineHarness
from src.app.schemas.user import UserResponse, UserSettingsRequest, UserSettingsResponse
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
            default_harness=(
                PipelineHarness(
                    kind=harness.kind,
                    version=harness.version,
                    config=harness.config,
                )
                if harness is not None
                else None
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
                default_harness=(
                    {
                        'kind': document.settings.default_harness.kind,
                        'version': document.settings.default_harness.version,
                        'config': document.settings.default_harness.config,
                    }
                    if document.settings.default_harness is not None
                    else None
                ),
            ),
        )
