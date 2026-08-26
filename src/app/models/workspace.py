"""Domain model for workspace execution defaults."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.app.models.pipeline import PipelineHarness


@dataclass(frozen=True, slots=True)
class WorkspaceDocument:
    """Workspace identity and metadata visible to its members."""

    id: str
    name: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class WorkspaceDefaults:
    """Optional execution overrides owned by one workspace."""

    workspace_id: str
    model_id: str | None
    harness: PipelineHarness | None
    updated_at: datetime
