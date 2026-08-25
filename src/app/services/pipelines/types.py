"""Application input values and errors for pipeline operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.app.models.execution import ModelTarget


@dataclass(frozen=True, slots=True)
class PipelineHarnessInput:
    """Harness selection supplied with a Pipeline mutation."""

    kind: str
    version: str
    config: dict[str, object]


@dataclass(frozen=True, slots=True)
class PipelineActivityDependencyInput:
    """Named condition required by one inline Activity definition."""

    activity: str
    condition: Literal['success', 'failure']


@dataclass(frozen=True, slots=True)
class PipelineActivityInput:
    """Activity definition supplied for one pipeline step."""

    name: str
    description: str
    type: str
    config: dict[str, object]
    model_target: ModelTarget | None = None
    harness: PipelineHarnessInput | None = None
    depends_on: tuple[PipelineActivityDependencyInput, ...] = ()


@dataclass(frozen=True, slots=True)
class PipelineCreate:
    """User-managed values required to create a pipeline."""

    name: str
    description: str
    steps: tuple[PipelineActivityInput, ...]
    model_target: ModelTarget | None = None
    harness: PipelineHarnessInput | None = None


@dataclass(frozen=True, slots=True)
class PipelinePatch:
    """Partial pipeline changes with supplied-field tracking."""

    provided_fields: frozenset[str]
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    steps: tuple[PipelineActivityInput, ...] | None = None
    model_target: ModelTarget | None = None
    harness: PipelineHarnessInput | None = None


class PipelineServiceError(Exception):
    """Base error raised by pipeline operations."""


class PipelineNotFoundError(PipelineServiceError):
    """Raised when a pipeline or retained changelog does not exist."""

    def __init__(self, *, pipeline_id: str) -> None:
        """Store the missing pipeline identifier."""

        super().__init__(f"Pipeline '{pipeline_id}' was not found.")
        self.pipeline_id = pipeline_id


class PipelineArchivedError(PipelineServiceError):
    """Raised when an archived pipeline receives a mutation."""

    def __init__(self, *, pipeline_id: str) -> None:
        """Store the immutable archived pipeline identifier."""

        super().__init__(f"Pipeline '{pipeline_id}' is archived.")
        self.pipeline_id = pipeline_id


class InvalidPipelineStepsError(PipelineServiceError):
    """Raised when a pipeline definition is invalid."""

    def __init__(self, *, field_name: str, message: str) -> None:
        """Store a field-specific validation failure."""

        super().__init__(f"Invalid pipeline field '{field_name}': {message}")
        self.field_name = field_name
        self.message = message
