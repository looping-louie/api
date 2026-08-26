"""Domain model for a persisted API user identity."""

from dataclasses import dataclass
from datetime import datetime

from src.app.models.pipeline import PipelineHarness


@dataclass(frozen=True, slots=True)
class UserSettings:
    """User-level execution defaults inherited by owned resources."""

    default_harness: PipelineHarness | None = None


@dataclass(frozen=True, slots=True)
class UserDocument:
    """Durable profile for an identity supplied with API requests."""

    id: str
    created_at: datetime
    updated_at: datetime
    settings: UserSettings = UserSettings()
