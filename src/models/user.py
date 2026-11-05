"""Domain model for a persisted API user identity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from src.models.pipeline import PipelineHarness


ModelAvailabilityStatus = Literal['enabled', 'disabled']
UserRole = Literal['admin', 'member']


@dataclass(frozen=True, slots=True)
class ConfiguredModelAvailability:
    """One User override for a logical model's availability."""

    id: str
    status: ModelAvailabilityStatus


@dataclass(frozen=True, slots=True)
class UserSettings:
    """User-level execution defaults inherited by owned resources."""

    default_model_id: str | None = None
    default_harness: PipelineHarness | None = None
    default_model_availability: ModelAvailabilityStatus = 'enabled'
    configured_models: tuple[ConfiguredModelAvailability, ...] = ()


@dataclass(frozen=True, slots=True)
class UserDocument:
    """Durable profile and optional local-account credentials."""

    id: str
    created_at: datetime
    updated_at: datetime
    settings: UserSettings = UserSettings()
    username: str | None = None
    password_hash: str | None = None
    role: UserRole = 'member'
    is_active: bool = True
