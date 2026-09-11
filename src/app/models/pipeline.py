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
PipelineHarnessKind = Literal['louie', 'codex_cli', 'copilot_cli']


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
    """Reference to one active User-owned Activity."""

    activity_id: str
    depends_on: tuple[PipelineStepDependency, ...] = ()


PipelineStep = PipelineActivityStep


@dataclass(frozen=True, slots=True)
class PipelineDocument:
    """Complete User-owned pipeline definition."""

    id: str
    name: str
    description: str
    status: PipelineStatus
    steps: tuple[PipelineStep, ...]
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    user_id: str = ''
    model_id: str | None = None
    harness: PipelineHarness | None = None

    def __post_init__(self) -> None:
        """Use the creator for legacy in-memory fixture ownership."""

        if not self.user_id:
            object.__setattr__(self, 'user_id', self.created_by)

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
    change_type: PipelineChangeType
    actor_id: str
    changed_at: datetime
    diff: JsonObject | None
    content: JsonObject | None
    user_id: str = ''

    def __post_init__(self) -> None:
        """Use the actor for legacy in-memory fixture ownership."""

        if not self.user_id:
            object.__setattr__(self, 'user_id', self.actor_id)
