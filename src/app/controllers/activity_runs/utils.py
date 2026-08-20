"""Shared schema translations for Activity-run controllers."""

from src.app.schemas.activity_run import (
    ActivityRunResponse,
    ActivityRunApplyOperationsResult,
    ActivityRunCommitResult,
    ActivityRunReviewInputResult,
)


def action_result(
    payload: dict[str, object],
) -> (
    ActivityRunApplyOperationsResult
    | ActivityRunReviewInputResult
    | ActivityRunCommitResult
):
    """Validate a non-snapshot action using its discriminator."""
    schemas = {
        'apply_operations': ActivityRunApplyOperationsResult,
        'submit_review_input': ActivityRunReviewInputResult,
        'commit_if_allowed': ActivityRunCommitResult,
    }
    schema = schemas.get(payload.get('action'))
    if schema is None:
        raise ValueError('result.action is not supported')
    return schema.model_validate(payload)


def activity_run_response(document: object) -> ActivityRunResponse:
    """Expose an activity-owned runtime artifact without its legacy loop alias."""

    response = ActivityRunResponse.model_validate(document)
    context = getattr(document, 'execution_context', {})
    artifacts = context.get('runtime_artifacts', {}) if isinstance(context, dict) else {}
    return response.model_copy(update={'payload': artifacts})
