"""HTTP request and response schemas for loop executions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from .shared import (
    ListResponse,
    NonEmptyString,
    PositiveInteger,
    RequestSchema,
    ResponseSchema,
)


LoopRunStatusValue = Literal['in_progress', 'failed', 'completed', 'stopped']
LoopRunStateValue = Literal['awaiting_snapshot']
LoopRunActionValue = Literal['collect_snapshot']


class LoopRunCreateRequest(RequestSchema):
    """User input that starts one execution of the selected loop."""

    input: NonEmptyString


class LoopRunResponse(ResponseSchema):
    """Persisted loop execution awaiting its first CLI checkpoint."""

    id: str
    loop_id: str
    input: str
    status: LoopRunStatusValue
    state: LoopRunStateValue
    next_action: LoopRunActionValue
    iteration: PositiveInteger
    token_revision: int
    created_at: datetime
    created_by: str
    updated_at: datetime


class LoopRunListResponse(ListResponse[LoopRunResponse]):
    """Fixed-size offset page of loop executions."""