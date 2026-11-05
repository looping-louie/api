"""Domain model for a user-owned opaque personal access token."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PersonalAccessToken:
    """A revocable API credential represented by a one-way digest."""

    id: str
    user_id: str
    name: str
    token_hash: str
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
