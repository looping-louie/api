"""Domain models for persisted pipelines and their changelog entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Mapping

from src.app.models.activity import ActivityDocument
from src.app.models.changelog import JsonObject


PipelineStatus = Literal["active", "disabled", "archived"]
PipelineChangeType = Literal[
    "created",
    "updated",
    "enabled",
    "disabled",
    "archived",
]
PipelineDependencyCondition = Literal['success', 'failure']
PipelineHarnessKind = Literal['louie']


@dataclass(frozen=True, slots=True)
class PipelineHarness:
    """Frozen local execution mechanism selected by a Pipeline."""

    kind: PipelineHarnessKind = 'louie'
    version: Literal['v1'] = 'v1'
    config: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PipelineStepDependency:
    """Execution condition required from one preceding Activity."""

    activity_id: str
    condition: PipelineDependencyCondition


@dataclass(frozen=True, slots=True)
class PipelineActivityStep:
    """Reference to one active workspace activity."""

    activity_id: str
    depends_on: tuple[PipelineStepDependency, ...] = ()


PipelineStep = PipelineActivityStep


@dataclass(frozen=True, slots=True)
class PipelineDocument:
    """Complete workspace-scoped pipeline definition."""

    id: str
    workspace_id: str
    name: str
    description: str
    status: PipelineStatus
    steps: tuple[PipelineStep, ...]
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    harness: PipelineHarness = field(default_factory=PipelineHarness)

    @property
    def enabled(self) -> bool:
        """Expose active state through the public boolean contract."""

        return self.status == "active"


@dataclass(frozen=True, slots=True)
class PipelineDetails:
    """Pipeline definition and Activity documents resolved in step order."""

    document: PipelineDocument
    activities: tuple[ActivityDocument, ...]


@dataclass(frozen=True, slots=True)
class PipelineChangelogEntry:
    """Immutable record of one pipeline mutation."""

    id: str
    pipeline_id: str
    workspace_id: str
    change_type: PipelineChangeType
    actor_id: str
    changed_at: datetime
    diff: JsonObject | None
    content: JsonObject | None
