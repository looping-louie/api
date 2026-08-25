"""HTTP schemas for workspace execution defaults."""

from __future__ import annotations

from datetime import datetime

from src.app.schemas.execution import (
    HarnessRequest,
    HarnessResponse,
    ModelTargetRequest,
    ModelTargetResponse,
)
from src.app.schemas.shared import RequestSchema, ResponseSchema


class WorkspaceDefaultsReplaceRequest(RequestSchema):
    """Complete optional workspace execution-default configuration."""

    model_target: ModelTargetRequest | None = None
    harness: HarnessRequest | None = None


class WorkspaceDefaultsResponse(ResponseSchema):
    """Workspace execution defaults, with null fields inheriting elsewhere."""

    model_target: ModelTargetResponse | None
    harness: HarnessResponse | None
    updated_at: datetime
