"""HTTP schemas for local-account authentication."""

from pydantic import Field

from .shared import RequestSchema, ResponseSchema


class AccountCredentialsRequest(RequestSchema):
    """Username and password accepted for setup and login."""

    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=12, max_length=1024)


class SessionUserResponse(ResponseSchema):
    """Authenticated account identity returned to the browser."""

    id: str
    username: str
    role: str


class SetupStatusResponse(ResponseSchema):
    """Whether the instance still accepts initial administrator setup."""

    setup_required: bool


class SessionStatusResponse(ResponseSchema):
    """Whether setup is required and which account owns the session."""

    setup_required: bool
    user: SessionUserResponse | None
