"""HTTP schemas for workspaces."""

from __future__ import annotations

from datetime import datetime

from pydantic import model_validator

from src.app.schemas.shared import NonEmptyString, RequestSchema, ResponseSchema


class WorkspaceCreateRequest(RequestSchema):
    """Fields required to create a User-owned workspace."""

    name: NonEmptyString


class WorkspaceResponse(ResponseSchema):
    """Workspace identity visible through the current user's collection."""

    id: str
    name: str
    created_at: datetime
    updated_at: datetime


class WorkspacePatchRequest(RequestSchema):
    """Mutable fields for one Workspace."""

    name: NonEmptyString | None = None

    @model_validator(mode='after')
    def require_name(self) -> 'WorkspacePatchRequest':
        """Require an explicit non-null Workspace name."""

        if 'name' not in self.model_fields_set or self.name is None:
            raise ValueError('Name must be supplied.')
        return self
