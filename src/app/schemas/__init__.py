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
from src.app.schemas.project import ProjectProfile, ProjectProfileMarkers
from src.app.schemas.metrics import ModelMetrics, RunMetrics
from src.app.schemas.reviewer import (
    ReviewerAssignment,
    ReviewerIssue,
    ReviewerMetrics,
    ReviewerResult,
)
from src.app.schemas.plan import ExecutionPlan, ProjectPhase
from src.app.schemas.harness import (
    RunRequest as RunHarnessRequest,
)
from src.app.schemas.meeting import (
    MeetingType,
    RunRequest as RunMeetingRequest,
    RunResponse as RunMeetingResponse,
)
from src.app.schemas.task import (
    CheckpointResponse as TaskCheckpointResponse,
    ContinueActionResult as TaskContinueActionResult,
    ContinueRequest as TaskContinueRequest,
    ContinueResponse as TaskContinueResponse,
    GetResponse as GetTaskResponse,
    StartRequest as TaskStartRequest,
    StartResponse as TaskStartResponse,
)

from .common import (
    DeleteResponse,
    ListResponse,
    ResourceSummaryResponse,
)
from .loop import (
    LoopAgentSchema,
    LoopChangelogEntryResponse,
    LoopChangelogListResponse,
    LoopCreateRequest,
    LoopListResponse,
    LoopOutputContractSchema,
    LoopPatchRequest,
    LoopResponse,
    LoopStopConditionsSchema,
)
from .persona import (
    PersonaCreateRequest,
    PersonaListResponse,
    PersonaPatchRequest,
    PersonaResponse,
    PersonaSummaryResponse,
)
from .skill import (
    SkillCreateRequest,
    SkillDefaultStrictness,
    SkillListResponse,
    SkillMetadata,
    SkillPatchRequest,
    SkillResponse,
    SkillSummaryResponse,
)
from .model import (
    ModelDeploymentResponse,
    ModelListResponse,
    ModelPricingResponse,
    ModelProviderAvailabilityResponse,
    ModelResponse,
    ModelSummaryResponse,
)

__all__ = [
    "DeleteResponse",
    "ListResponse",
    "LoopAgentSchema",
    "LoopChangelogEntryResponse",
    "LoopChangelogListResponse",
    "LoopCreateRequest",
    "LoopListResponse",
    "LoopOutputContractSchema",
    "LoopPatchRequest",
    "LoopResponse",
    "LoopStopConditionsSchema",
    "PersonaCreateRequest",
    "PersonaListResponse",
    "PersonaPatchRequest",
    "PersonaResponse",
    "PersonaSummaryResponse",
    "ResourceSummaryResponse",
    "SkillCreateRequest",
    "SkillDefaultStrictness",
    "SkillListResponse",
    "SkillMetadata",
    "SkillPatchRequest",
    "SkillResponse",
    "SkillSummaryResponse",
    "ModelDeploymentResponse",
    "ModelListResponse",
    "ModelPricingResponse",
    "ModelProviderAvailabilityResponse",
    "ModelResponse",
    "ModelSummaryResponse",
]

__all__ = [
    'ExecutionPlan',
    'GeneratorAssignment',
    'MeetingType',
    'ModelMetrics',
    'ProjectProfile',
    'ProjectProfileMarkers',
    'ProjectPhase',
    'ReviewerAssignment',
    'ReviewerIssue',
    'ReviewerMetrics',
    'ReviewerResult',
    'GetTaskResponse',
    'RunHarnessRequest',
    'RunMeetingRequest',
    'RunMeetingResponse',
    'TaskCheckpointResponse',
    'TaskContinueActionResult',
    'TaskContinueRequest',
    'TaskContinueResponse',
    'TaskStartRequest',
    'TaskStartResponse',
    'RunMetrics',
]
