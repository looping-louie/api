"""Persistence protocol for workspace execution defaults."""

from __future__ import annotations

from typing import Protocol

from src.app.models.workspace import WorkspaceDefaults, WorkspaceDocument


class WorkspaceRepository(Protocol):
    """Store workspace-owned configuration."""

    async def create(
        self,
        *,
        workspace: WorkspaceDocument,
        owner_id: str,
    ) -> WorkspaceDocument:
        """Create a workspace and its owner's membership atomically."""
        raise NotImplementedError

    async def list_for_user(self, *, user_id: str) -> list[WorkspaceDocument]:
        """Return all workspaces accessible to one user."""
        raise NotImplementedError

    async def get_workspace(
        self,
        *,
        workspace_id: str,
    ) -> WorkspaceDocument:
        """Return one Workspace that is known to have an active membership."""
        raise NotImplementedError

    async def update_workspace(
        self,
        *,
        workspace: WorkspaceDocument,
    ) -> WorkspaceDocument:
        """Persist mutable Workspace fields and return the updated document."""
        raise NotImplementedError

    async def get_defaults(
        self,
        *,
        workspace_id: str,
    ) -> WorkspaceDefaults | None:
        """Return stored defaults when the workspace has configured them."""
        raise NotImplementedError

    async def replace_defaults(
        self,
        *,
        defaults: WorkspaceDefaults,
    ) -> WorkspaceDefaults:
        """Insert or replace the complete workspace default configuration."""
        raise NotImplementedError
