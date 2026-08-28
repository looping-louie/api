"""User HTTP response mapping."""

from src.app.models.user import UserDocument
from src.app.schemas.user import UserResponse, UserSettingsResponse


def user_response(document: UserDocument) -> UserResponse:
    """Map a User document to its public representation."""

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