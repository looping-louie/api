"""Persistence protocol for Workers and Project enablements."""

from datetime import datetime
from typing import Mapping, Protocol

from src.app.models.worker import WorkerHarnessCapability, WorkerReadinessDocument
from src.app.models.worker_instance import (
    WorkerInstanceDocument,
    WorkerInstanceProjectDocument,
    WorkerProjectEnablementDocument,
)


class WorkerInstanceRepository(Protocol):
    """Persist globally identified Workers and their Project assignments."""

    async def get(
        self,
        *,
        worker_instance_id: str,
    ) -> WorkerInstanceDocument | None:
        """Return one globally identified Worker."""
        raise NotImplementedError

    async def get_for_owner(
        self,
        *,
        worker_instance_id: str,
        owner_user_id: str,
    ) -> WorkerInstanceDocument | None:
        """Return one Worker owned by the specified User."""
        raise NotImplementedError

    async def list_for_owner(
        self,
        *,
        owner_user_id: str,
    ) -> tuple[WorkerInstanceDocument, ...]:
        """Return Workers owned by the specified User."""
        raise NotImplementedError

    async def create(
        self,
        document: WorkerInstanceDocument,
    ) -> WorkerInstanceDocument:
        """Persist one newly registered Worker."""
        raise NotImplementedError

    async def heartbeat(
        self,
        *,
        worker_instance_id: str,
        occurred_at: datetime,
        harnesses: tuple[WorkerHarnessCapability, ...],
    ) -> WorkerInstanceDocument | None:
        """Refresh one Worker's liveness and observed Harnesses."""
        raise NotImplementedError

    async def get_enabled(
        self,
        *,
        worker_instance_id: str,
        project_id: str,
    ) -> WorkerInstanceDocument | None:
        """Return one Worker when it is enabled for the specified Project."""
        raise NotImplementedError

    async def readiness(
        self,
        *,
        project_id: str,
        active_since: datetime,
        harness: Mapping[str, object],
    ) -> WorkerReadinessDocument:
        """Summarize enabled Worker liveness and exact Harness matches."""
        raise NotImplementedError

    async def enable_project(
        self,
        document: WorkerProjectEnablementDocument,
    ) -> WorkerProjectEnablementDocument:
        """Allow a Worker to claim work for one Project."""
        raise NotImplementedError

    async def disable_project(
        self,
        *,
        worker_instance_id: str,
        project_id: str,
    ) -> None:
        """Remove one Worker's authorization to claim Project work."""
        raise NotImplementedError

    async def list_enabled_projects(
        self,
        *,
        worker_instance_id: str,
    ) -> tuple[WorkerProjectEnablementDocument, ...]:
        """Return the Projects enabled for one Worker."""
        raise NotImplementedError

    async def list_enabled(
        self,
        *,
        project_id: str,
    ) -> tuple[WorkerInstanceProjectDocument, ...]:
        """Return Workers enabled for one Project."""
        raise NotImplementedError
