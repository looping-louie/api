"""Persistence interfaces for pipeline execution records."""

from .repository import PipelineRunRepository
from .sqlite_repository import SqlitePipelineRunRepository

__all__ = ['PipelineRunRepository', 'SqlitePipelineRunRepository']
