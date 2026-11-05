"""Domain model for a runtime-specific service account."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ServiceAccount:
    """A project-scoped runtime credential stored as a digest."""

    id: str
    administrator_id: str
    name: str
    token_hash: str
    project_ids: tuple[str, ...]
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
