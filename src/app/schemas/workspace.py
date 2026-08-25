"""HTTP schemas for workspace execution defaults."""

from __future__ import annotations

from datetime import datetime

from src.app.schemas.pipeline import PipelineHarnessRequest, PipelineHarnessResponse
from src.app.schemas.shared import NonEmptyString, RequestSchema, ResponseSchema


class ModelTargetRequest(RequestSchema):
    """One explicit provider connection and logical model selection."""

    linked_service_id: NonEmptyString
    model_id: NonEmptyString


class ModelTargetResponse(ResponseSchema):
    """One effective provider connection and logical model selection."""

    linked_service_id: str
    model_id: str


class WorkspaceDefaultsReplaceRequest(RequestSchema):
    """Complete optional workspace execution-default configuration."""

    model_target: ModelTargetRequest | None = None
    harness: PipelineHarnessRequest | None = None


class WorkspaceDefaultsResponse(ResponseSchema):
    """Workspace execution defaults, with null fields inheriting elsewhere."""

    model_target: ModelTargetResponse | None
    harness: PipelineHarnessResponse | None
    updated_at: datetime
