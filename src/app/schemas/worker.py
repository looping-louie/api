"""HTTP schemas for runtime worker registration."""

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .shared import RequestSchema, ResponseSchema


class WorkerHarnessCapabilityRequest(RequestSchema):
    """One Harness capability reported during Worker registration."""

    kind: Literal['louie', 'codex_cli'] = 'louie'
    version: Literal['v1'] = 'v1'
    config: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode='after')
    def require_empty_harness_config(self) -> 'WorkerHarnessCapabilityRequest':
        """Reject settings not supported by the initial Harness contract."""

        if self.config:
            raise ValueError(f'{self.kind} harness config must be empty.')
        return self


class WorkerHarnessCapabilityResponse(ResponseSchema):
    """One persisted Harness capability advertised by a Worker."""

    kind: Literal['louie', 'codex_cli']
    version: Literal['v1']
    config: dict[str, object]


class WorkerCreateRequest(RequestSchema):
    """Capabilities declared for one newly provisioned Worker."""

    harnesses: list[WorkerHarnessCapabilityRequest] = Field(
        default_factory=lambda: [WorkerHarnessCapabilityRequest()],
    )


class WorkerResponse(ResponseSchema):
    """One workspace worker registration and its most recent heartbeat."""

    id: str
    registered_at: datetime
    last_heartbeat_at: datetime
    harnesses: list[WorkerHarnessCapabilityResponse]
