"""HTTP schemas for the current API user profile."""

from datetime import datetime

from src.app.schemas.execution import HarnessRequest, HarnessResponse
from src.app.schemas.shared import RequestSchema, ResponseSchema


class UserSettingsRequest(RequestSchema):
    """Mutable user-level execution defaults."""

    default_harness: HarnessRequest | None = None


class UserSettingsResponse(ResponseSchema):
    """Persisted user-level execution defaults."""

    default_harness: HarnessResponse | None


class UserResponse(ResponseSchema):
    """Durable representation of a request identity."""

    id: str
    created_at: datetime
    updated_at: datetime
    settings: UserSettingsResponse
