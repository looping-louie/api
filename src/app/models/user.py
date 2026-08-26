"""Domain model for a persisted API user identity."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class UserDocument:
    """Durable profile for an identity supplied with API requests."""

    id: str
    created_at: datetime
    updated_at: datetime