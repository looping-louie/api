"""Persistence protocol for workspace execution defaults."""

from __future__ import annotations

from typing import Protocol

from src.app.models.workspace import WorkspaceDefaults


class WorkspaceRepository(Protocol):
    """Store workspace-owned configuration."""

    async def get(
        self,
        *,
        workspace_id: str,
    ) -> WorkspaceDefaults | None:
        """Return stored defaults when the workspace has configured them."""
        ...

    async def replace(
        self,
        *,
        defaults: WorkspaceDefaults,
    ) -> WorkspaceDefaults:
        """Insert or replace the complete workspace default configuration."""
        ...
