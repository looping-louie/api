"""HTTP schemas for runtime worker registration."""

from datetime import datetime
from typing import Literal

from .execution import HarnessRequest, HarnessResponse
from .shared import NonEmptyString, RequestSchema, ResponseSchema


class WorkerHarnessCapabilityRequest(HarnessRequest):
    """One Harness capability reported during Worker registration."""

    kind: Literal['louie', 'codex_cli', 'copilot_cli']


class WorkerInstanceCreateRequest(RequestSchema):
    """Initial Project assignment and capabilities for one Worker."""

    project_id: NonEmptyString
    harnesses: list[WorkerHarnessCapabilityRequest]


class WorkerHeartbeatRequest(RequestSchema):
    """Current Harness capabilities observed by an existing Worker."""

    harnesses: list[WorkerHarnessCapabilityRequest]


class WorkerHarnessCapabilityResponse(HarnessResponse):
    """One persisted Harness capability advertised by a Worker."""


class WorkerResponse(ResponseSchema):
    """One workspace worker registration and its most recent heartbeat."""

    id: str
    registered_at: datetime
    last_heartbeat_at: datetime
    harnesses: list[WorkerHarnessCapabilityResponse]


class WorkerProjectEnablementResponse(ResponseSchema):
    """One Project that is authorized to receive work from a Worker."""

    worker_id: str
    project_id: str
    enabled_at: datetime


class WorkerInstanceProjectResponse(WorkerResponse):
    """A Worker visible through one enabled Project."""

    enabled_at: datetime
    active: bool
    active_claims: int
    capacity: int
