"""Persistence interfaces for activity-owned executions."""

from .repository import ActivityRunRepository
from .sqlite_repository import SqliteActivityRunRepository

__all__ = ['ActivityRunRepository', 'SqliteActivityRunRepository']