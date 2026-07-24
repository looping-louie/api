"""Domain models for persisted pipelines and their changelog entries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from src.app.models.changelog import JsonObject


PipelineStatus = Literal["active", "disabled", "archived"]
PipelineChangeType = Literal[
    "created",
    "updated",
    "enabled",
    "disabled",
    "archived",
]


@dataclass(frozen=True, slots=True)
class PipelineQuizConfig:
    """Validated quiz-generation limits stored in a pipeline."""

    minimum_correct_answers: int
    question_count: int
    option_count: int


@dataclass(frozen=True, slots=True)
class PipelineLoopStep:
    """Reference to one active loop."""

    type: Literal["loop"]
    loop_id: str


@dataclass(frozen=True, slots=True)
class PipelineHumanGateStep:
    """Approval or quiz checkpoint in a pipeline."""

    type: Literal["human_gate"]
    gate_type: Literal["approval", "quiz"]
    config: PipelineQuizConfig | None


PipelineStep = PipelineLoopStep | PipelineHumanGateStep


@dataclass(frozen=True, slots=True)
class PipelineDocument:
    """Complete workspace-scoped pipeline definition."""

    id: str
    workspace_id: str
    title: str
    description: str
    status: PipelineStatus
    steps: tuple[PipelineStep, ...]
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str

    @property
    def enabled(self) -> bool:
        """Expose active state through the public boolean contract."""

        return self.status == "active"


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
