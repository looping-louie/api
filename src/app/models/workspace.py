"""Domain model for workspace execution defaults."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.app.models.execution import ModelTarget
from src.app.models.pipeline import PipelineHarness

@dataclass(frozen=True, slots=True)
class WorkspaceDefaults:
    """Optional execution overrides owned by one workspace."""

    workspace_id: str
    model_target: ModelTarget | None
    harness: PipelineHarness | None
    updated_at: datetime
