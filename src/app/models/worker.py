"""Domain model for workspace-scoped runtime workers."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WorkerDocument:
    """One durable runtime identity and its most recent liveness signal."""

    id: str
    workspace_id: str
    registered_at: datetime
    last_heartbeat_at: datetime
