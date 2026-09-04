"""Domain models for workspace-scoped runtime workers."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Mapping


@dataclass(frozen=True, slots=True)
class WorkerHarnessCapability:
    """One local Harness capability advertised by a Worker."""

    kind: Literal['louie', 'codex_cli'] = 'louie'
    version: Literal['v1'] = 'v1'
    config: Mapping[str, object] = field(default_factory=dict)

    def matches(self, harness: Mapping[str, object]) -> bool:
        """Return whether this capability exactly matches a frozen Harness."""

        return (
            self.kind == harness.get('kind')
            and self.version == harness.get('version')
            and dict(self.config) == harness.get('config')
        )


def default_worker_harnesses() -> tuple[WorkerHarnessCapability, ...]:
    """Return the compatibility capability set for existing Workers."""

    return (WorkerHarnessCapability(),)


@dataclass(frozen=True)
class WorkerDocument:
    """One durable runtime identity and its most recent liveness signal."""

    id: str
    project_id: str
    registered_at: datetime
    last_heartbeat_at: datetime
    harnesses: tuple[WorkerHarnessCapability, ...] = field(
        default_factory=default_worker_harnesses,
    )


@dataclass(frozen=True, slots=True)
class WorkerReadinessDocument:
    """Aggregated worker liveness and Harness compatibility for a workspace."""

    registered_worker_count: int
    active_worker_count: int
    compatible_worker_count: int
    latest_heartbeat_at: datetime | None
