"""Persistence protocol for global Workers and Project enablements."""

from typing import Protocol

from src.app.models.worker_instance import (
    WorkerInstanceDocument,
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

    async def create(
        self,
        document: WorkerInstanceDocument,
    ) -> WorkerInstanceDocument:
        """Persist one newly registered Worker."""
        raise NotImplementedError

    async def enable_project(
        self,
        document: WorkerProjectEnablementDocument,
    ) -> WorkerProjectEnablementDocument:
        """Allow a Worker to claim work for one Project."""
        raise NotImplementedError

    async def list_enabled_projects(
        self,
        *,
        worker_instance_id: str,
    ) -> tuple[WorkerProjectEnablementDocument, ...]:
        """Return the Projects enabled for one Worker."""
        raise NotImplementedError