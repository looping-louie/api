"""HTTP schemas for runtime worker registration."""

from datetime import datetime

from pydantic import Field

from .execution import HarnessRequest, HarnessResponse
from .shared import RequestSchema, ResponseSchema


class WorkerHarnessCapabilityRequest(HarnessRequest):
    """One Harness capability reported during Worker registration."""


class WorkerHarnessCapabilityResponse(HarnessResponse):
    """One persisted Harness capability advertised by a Worker."""


class WorkerCreateRequest(RequestSchema):
    """Capabilities declared for one newly provisioned Worker."""

    harnesses: list[WorkerHarnessCapabilityRequest] = Field(
        default_factory=lambda: [WorkerHarnessCapabilityRequest()],
    )


class WorkerHeartbeatRequest(RequestSchema):
    """Current Harness capabilities observed by an existing Worker."""

    harnesses: list[WorkerHarnessCapabilityRequest]


class WorkerResponse(ResponseSchema):
    """One workspace worker registration and its most recent heartbeat."""

    id: str
    registered_at: datetime
    last_heartbeat_at: datetime
    harnesses: list[WorkerHarnessCapabilityResponse]
