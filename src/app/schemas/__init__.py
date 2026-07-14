"""
Public API schemas.

These models define the contract between the HTTP API and clients.

The runner internally exchanges richer Python objects, but every request
and response crossing the API boundary is validated through these schemas.

The hierarchy is intentionally split into:
- requests
- metrics
- reviewer results
- execution trace
- run response
"""

from src.app.schemas.generator import GeneratorAssignment
from src.app.schemas.metrics import ModelMetrics, RunMetrics
from src.app.schemas.reviewer import (
    ReviewerAssignment,
    ReviewerIssue,
    ReviewerMetrics,
    ReviewerResult,
)
from src.app.schemas.plan import ExecutionPlan, IterationTrace, ProjectPhase
from src.app.schemas.harness import (
    RunRequest as RunHarnessRequest,
    RunResponse as RunHarnessResponse,
)
from src.app.schemas.meeting import (
    MeetingType,
    RunRequest as RunMeetingRequest,
    RunResponse as RunMeetingResponse,
)
from src.app.schemas.workflow import (
    RunRequest as RunWorkflowRequest,
    RunResponse as RunWorkflowResponse,
)


__all__ = [
    'ExecutionPlan',
    'GeneratorAssignment',
    'IterationTrace',
    'MeetingType',
    'ModelMetrics',
    'ProjectPhase',
    'ReviewerAssignment',
    'ReviewerIssue',
    'ReviewerMetrics',
    'ReviewerResult',
    'RunHarnessRequest',
    'RunHarnessResponse',
    'RunMeetingRequest',
    'RunMeetingResponse',
    'RunMetrics',
    'RunWorkflowRequest',
    'RunWorkflowResponse',
]
