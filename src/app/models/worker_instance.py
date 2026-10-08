"""Domain models for globally identified Workers."""

from dataclasses import dataclass
from datetime import datetime

from src.app.models.worker import WorkerHarnessCapability


@dataclass(frozen=True, slots=True)
class WorkerInstanceDocument:
    """One Worker process and its latest advertised capabilities."""

    id: str
    registered_at: datetime
    last_heartbeat_at: datetime
    harnesses: tuple[WorkerHarnessCapability, ...]


@dataclass(frozen=True, slots=True)
class WorkerProjectEnablementDocument:
    """Allow one Worker to claim work for one Project."""

    worker_instance_id: str
    project_id: str
    enabled_at: datetime


@dataclass(frozen=True, slots=True)
class WorkerInstanceProjectDocument:
    """One Worker and its authorization for a Project."""

    worker: WorkerInstanceDocument
    enablement: WorkerProjectEnablementDocument
