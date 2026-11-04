"""Domain model for user-owned linked services."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LinkedService:
    """Encrypted provider connection owned by one user."""

    id: str
    user_id: str
    name: str
    provider_type: str
    enabled: bool
    key_trimmed: str | None
    key_ciphertext: str | None
    key_version: int
    base_url: str | None
    version: int
    created_at: datetime
    updated_at: datetime
