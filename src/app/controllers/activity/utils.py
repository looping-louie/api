"""Shared request translations for activity controllers."""

from src.app.schemas.activity import ActivityPatchRequest


def activity_changes(payload: ActivityPatchRequest) -> dict[str, object]:
    """Translate supplied patch fields to service changes."""
    changes = payload.model_dump(exclude_unset=True)
    if 'config' in changes:
        config = payload.config
        if config is None:
            raise ValueError('config must not be null')
        changes['config'] = config.model_dump(by_alias=True)
    return changes
