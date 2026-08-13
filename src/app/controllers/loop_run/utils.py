"""Shared schema translations for loop-run controllers."""

from src.app.schemas.loop_run import (
    LoopRunApplyOperationsResult,
    LoopRunCommitResult,
    LoopRunResponse,
    LoopRunReviewInputResult,
)


def action_result(
    payload: dict[str, object],
) -> LoopRunApplyOperationsResult | LoopRunReviewInputResult | LoopRunCommitResult:
    """Validate a non-snapshot action using its discriminator."""
    schemas = {
        'apply_operations': LoopRunApplyOperationsResult,
        'submit_review_input': LoopRunReviewInputResult,
        'commit_if_allowed': LoopRunCommitResult,
    }
    schema = schemas.get(payload.get('action'))
    if schema is None:
        raise ValueError('result.action is not supported')
    return schema.model_validate(payload)


def loop_run_response(document: object) -> LoopRunResponse:
    """Expose runtime artifacts without leaking full execution context."""
    response = LoopRunResponse.model_validate(document)
    context = getattr(document, 'execution_context', {})
    artifacts = context.get('runtime_artifacts', {}) if isinstance(context, dict) else {}
    return response.model_copy(update={'payload': artifacts})
