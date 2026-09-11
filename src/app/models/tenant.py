"""Domain models for workspace tenancy."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Project context resolved for the authenticated user."""

    project_id: str
    user_id: str


@dataclass(frozen=True, slots=True)
class WorkspaceMembership:
    """Relationship between a user and an accessible workspace."""

    user_id: str
    project_id: str
    is_enabled: bool = True
    is_default: bool = False
