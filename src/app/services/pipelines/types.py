"""Application input values and errors for pipeline operations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PipelineQuizConfigInput:
    """Quiz values accepted by create and patch operations."""

    minimum_correct_answers: int
    question_count: int = 10
    option_count: int = 3


@dataclass(frozen=True, slots=True)
class PipelineStepInput:
    """Untrusted pipeline step values passed to the service."""

    type: str
    loop_id: str | None = None
    gate_type: str | None = None
    config: PipelineQuizConfigInput | None = None


@dataclass(frozen=True, slots=True)
class PipelineCreate:
    """User-managed values required to create a pipeline."""

    title: str
    description: str
    steps: tuple[PipelineStepInput, ...]


@dataclass(frozen=True, slots=True)
class PipelinePatch:
    """Partial pipeline changes with supplied-field tracking."""

    provided_fields: frozenset[str]
    title: str | None = None
    description: str | None = None
    enabled: bool | None = None
    steps: tuple[PipelineStepInput, ...] | None = None


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


class UnsupportedPipelineStepError(PipelineServiceError):
    """Raised when a step discriminator is unsupported."""

    def __init__(self, *, step_type: object) -> None:
        """Store the rejected discriminator."""

        super().__init__(f"Unsupported pipeline step type '{step_type}'.")
        self.step_type = step_type


class UnsupportedHumanGateTypeError(PipelineServiceError):
    """Raised when a human gate discriminator is unsupported."""

    def __init__(self, *, gate_type: object) -> None:
        """Store the rejected gate type."""

        super().__init__(f"Unsupported human gate type '{gate_type}'.")
        self.gate_type = gate_type
