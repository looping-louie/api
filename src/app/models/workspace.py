"""Domain model for workspace execution defaults."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.app.models.pipeline import PipelineHarness


@dataclass(frozen=True, slots=True)
class ModelTarget:
    """One provider connection and logical model selected for execution."""

    linked_service_id: str
    model_id: str


@dataclass(frozen=True, slots=True)
class WorkspaceDefaults:
    """Optional execution overrides owned by one workspace."""

    workspace_id: str
    model_target: ModelTarget | None
    harness: PipelineHarness | None
    updated_at: datetime
