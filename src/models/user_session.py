"""Domain model for a server-side browser session."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class UserSession:
    """A session represented by a one-way token digest."""

    id: str
    user_id: str
    token_hash: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
