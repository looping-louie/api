"""HTTP schemas for local-account authentication."""

from datetime import datetime

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


class LocalAccountResponse(SessionUserResponse):
    """Administrator-visible local account metadata."""

    is_active: bool


class MemberAccountCreateRequest(AccountCredentialsRequest):
    """Credentials for an administrator-provisioned member account."""


class MemberAccountPasswordResetRequest(RequestSchema):
    """Administrator-provided replacement password for one member."""

    password: str = Field(min_length=12, max_length=1024)


class MemberAccountActivationRequest(RequestSchema):
    """Requested active state for one administrator-managed member."""

    is_active: bool


class PersonalAccessTokenCreateRequest(RequestSchema):
    """Name and optional expiry for a new personal access token."""

    name: str = Field(min_length=1, max_length=140)
    expires_at: datetime | None = None


class PersonalAccessTokenResponse(ResponseSchema):
    """Credential-safe personal access-token metadata."""

    id: str
    name: str
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None


class PersonalAccessTokenCreatedResponse(PersonalAccessTokenResponse):
    """One-time display of a newly issued opaque token."""

    token: str


class ServiceAccountCreateRequest(RequestSchema):
    """Administrator-provided runtime credential configuration."""

    name: str = Field(min_length=1, max_length=140)
    project_ids: list[str] = Field(min_length=1)
    expires_at: datetime | None = None


class ServiceAccountResponse(ResponseSchema):
    """Credential-safe runtime service-account metadata."""

    id: str
    name: str
    project_ids: list[str]
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None


class ServiceAccountCreatedResponse(ServiceAccountResponse):
    """One-time display of a newly issued runtime credential."""

    token: str


class SetupStatusResponse(ResponseSchema):
    """Whether the instance still accepts initial administrator setup."""

    setup_required: bool


class SessionStatusResponse(ResponseSchema):
    """Whether setup is required and which account owns the session."""

    setup_required: bool
    user: SessionUserResponse | None
