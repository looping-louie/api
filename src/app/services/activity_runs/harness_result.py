"""Validate normalized Harness observations persisted by Activity runs."""

from __future__ import annotations

from collections.abc import Mapping

from src.app.services.activity_runs.types import ActivityRunValidationError


def codex_runtime_artifacts(
    *,
    activity_snapshot: Mapping[str, object],
    result: Mapping[str, object],
    require_commit_message: bool,
) -> dict[str, object]:
    """Validate Codex model observations and its optional commit proposal."""

    expected_model = activity_snapshot.get('requested_model')
    requested_model = result.get('requested_model')
    actual_model = result.get('actual_model')
    if not isinstance(expected_model, str) or not expected_model.strip():
        raise RuntimeError('Codex Activity snapshot is missing requested_model.')
    if requested_model != expected_model:
        raise ActivityRunValidationError(
            field_name='result.requested_model',
            message='must match the frozen requested model',
        )
    if not isinstance(actual_model, str) or not actual_model.strip():
        raise ActivityRunValidationError(
            field_name='result.actual_model',
            message='must not be empty',
        )
    artifacts: dict[str, object] = {
        'requested_model': requested_model,
        'actual_model': actual_model,
    }
    if require_commit_message:
        commit_message = result.get('commit_message')
        if not isinstance(commit_message, str) or not commit_message.strip():
            raise ActivityRunValidationError(
                field_name='result.commit_message',
                message='must not be empty',
            )
        artifacts['commit_message'] = commit_message
    return artifacts
