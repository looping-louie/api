"""Shared schema translations for Activity-run controllers."""

from src.app.schemas.activity_run import (
    ActivityRunResponse,
    ActivityRunApplyOperationsResult,
    ActivityRunCommitResult,
    ActivityRunHarnessResult,
    ActivityRunReviewInputResult,
)


def action_result(
    payload: dict[str, object],
) -> (
    ActivityRunApplyOperationsResult
    | ActivityRunHarnessResult
    | ActivityRunReviewInputResult
    | ActivityRunCommitResult
):
    """Validate a non-snapshot action using its discriminator."""
    schemas = {
        'apply_operations': ActivityRunApplyOperationsResult,
        'run_harness': ActivityRunHarnessResult,
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
    if getattr(document, 'next_action', None) == 'run_harness':
        snapshot = getattr(document, 'activity_snapshot', {})
        harness = snapshot.get('harness') if isinstance(snapshot, dict) else None
        return response.model_copy(update={'payload': {
            'harness': harness,
            'repo_context': context.get('repo_context', ''),
            'constitution': context.get('constitution', ''),
            'project_profile': context.get('project_profile', {}),
        }})
    return response.model_copy(update={'payload': artifacts})
