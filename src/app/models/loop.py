"""Domain models for persisted loop definitions and changelog entries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from src.app.models.changelog import JsonObject


LoopFlow = Literal["direct", "refinement", "roundtable"]
LoopStatus = Literal["active", "disabled", "archived"]
LoopAgentRole = Literal["generator", "reviewer", "aggregator"]
LoopOutputType = Literal["text", "json", "files"]
LoopChangeType = Literal[
    "created",
    "updated",
    "enabled",
    "disabled",
    "archived",
    "deleted",
]
@dataclass(frozen=True, slots=True)
class LoopStopConditions:
    """Optional limits stored for a loop without enforcing them."""

    max_iterations: int | None = None
    max_tokens: int | None = None
    timeout_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class LoopAgent:
    """One model and persona assigned to a role in a loop."""

    id: str
    model_id: str
    persona_id: str
    role: LoopAgentRole


@dataclass(frozen=True, slots=True)
class LoopOutputContract:
    """Generic description of the output a loop must produce."""

    type: LoopOutputType
    description: str
    files: tuple[str, ...]
    schema: JsonObject | None


@dataclass(frozen=True, slots=True)
class LoopDocument:
    """Complete workspace-scoped loop definition."""

    id: str
    workspace_id: str
    title: str
    description: str
    flow: LoopFlow
    status: LoopStatus
    stop_conditions: LoopStopConditions
    agents: tuple[LoopAgent, ...]
    output_contract: LoopOutputContract
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


@dataclass(frozen=True, slots=True)
class LoopChangelogEntry:
    """Immutable record of one loop mutation."""

    id: str
    loop_id: str
    workspace_id: str
    change_type: LoopChangeType
    actor_id: str
    changed_at: datetime
    diff: JsonObject | None
    content: JsonObject | None
