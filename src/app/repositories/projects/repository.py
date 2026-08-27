"""Persistence protocol for projects."""

from __future__ import annotations

from typing import Protocol

from src.app.models.project import ProjectDocument


class ProjectRepository(Protocol):
    """Store User-owned project metadata."""

    async def create(
        self,
        *,
        project: ProjectDocument,
        owner_id: str,
    ) -> ProjectDocument:
        """Create a Project and its owner's membership atomically."""
        raise NotImplementedError

    async def list_for_user(self, *, user_id: str) -> list[ProjectDocument]:
        """Return all Projects accessible to one User."""
        raise NotImplementedError

    async def get_project(
        self,
        *,
        project_id: str,
    ) -> ProjectDocument:
        """Return one Project that is known to have an active membership."""
        raise NotImplementedError

    async def update_project(
        self,
        *,
        project: ProjectDocument,
    ) -> ProjectDocument:
        """Persist mutable Project fields and return the updated document."""
        raise NotImplementedError
