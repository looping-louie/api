"""Shared request translations for activity controllers."""

from src.app.schemas.activity import ActivityPatchRequest


def activity_changes(payload: ActivityPatchRequest) -> dict[str, object]:
    """Translate supplied patch fields to service changes."""
    changes = payload.model_dump(exclude_unset=True)
    return changes
