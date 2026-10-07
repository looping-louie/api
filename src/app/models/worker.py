"""Domain models for global Worker capabilities and readiness."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Mapping


@dataclass(frozen=True, slots=True)
class WorkerHarnessCapability:
    """One local Harness capability advertised by a Worker."""

    kind: Literal['louie', 'codex_cli', 'copilot_cli']
    version: Literal['v1'] = 'v1'
    config: Mapping[str, object] = field(default_factory=dict)

    def matches(self, harness: Mapping[str, object]) -> bool:
        """Return whether this capability exactly matches a frozen Harness."""

        return (
            self.kind == harness.get('kind')
            and self.version == harness.get('version')
            and dict(self.config) == harness.get('config')
        )


@dataclass(frozen=True, slots=True)
class WorkerReadinessDocument:
    """Aggregated worker liveness and Harness compatibility for a workspace."""

    registered_worker_count: int
    active_worker_count: int
    compatible_worker_count: int
    latest_heartbeat_at: datetime | None
