"""Persistence access for workspace execution defaults."""

from .repository import WorkspaceRepository
from .sqlite_repository import SqliteWorkspaceRepository

__all__ = ['SqliteWorkspaceRepository', 'WorkspaceRepository']
