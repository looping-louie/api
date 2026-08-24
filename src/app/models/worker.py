"""Domain models for workspace-scoped runtime workers."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Mapping


@dataclass(frozen=True, slots=True)
class WorkerHarnessCapability:
    """One local Harness capability advertised by a Worker."""

    kind: Literal['louie'] = 'louie'
    version: Literal['v1'] = 'v1'
    config: Mapping[str, object] = field(default_factory=dict)


def default_worker_harnesses() -> tuple[WorkerHarnessCapability, ...]:
    """Return the compatibility capability set for existing Workers."""

    return (WorkerHarnessCapability(),)


@dataclass(frozen=True)
class WorkerDocument:
    """One durable runtime identity and its most recent liveness signal."""

    id: str
    workspace_id: str
    registered_at: datetime
    last_heartbeat_at: datetime
    harnesses: tuple[WorkerHarnessCapability, ...] = field(
        default_factory=default_worker_harnesses,
    )
