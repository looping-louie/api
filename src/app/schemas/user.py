"""HTTP schemas for the current API user profile."""

from datetime import datetime

from src.app.schemas.shared import ResponseSchema


class UserResponse(ResponseSchema):
    """Durable representation of a request identity."""

    id: str
    created_at: datetime
    updated_at: datetime