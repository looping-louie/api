"""Shared request translations for activity controllers."""

from src.app.schemas.activity import ActivityPatchRequest
from src.app.models.execution import ModelTarget
from src.app.models.pipeline import PipelineHarness


def activity_changes(payload: ActivityPatchRequest) -> dict[str, object]:
    """Translate supplied patch fields to service changes."""
    changes = payload.model_dump(exclude_unset=True)
    if 'model_target' in payload.model_fields_set:
        changes['model_target'] = (
            ModelTarget(
                linked_service_id=payload.model_target.linked_service_id,
                model_id=payload.model_target.model_id,
            )
            if payload.model_target is not None
            else None
        )
    if 'harness' in payload.model_fields_set:
        changes['harness'] = (
            PipelineHarness(
                kind=payload.harness.kind,
                version=payload.harness.version,
                config=payload.harness.config,
            )
            if payload.harness is not None
            else None
        )
    return changes
