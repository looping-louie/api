"""Validate normalized Harness observations persisted by Activity runs."""

from __future__ import annotations

from collections.abc import Mapping

from src.app.services.activity_runs.types import ActivityRunValidationError


def harness_runtime_artifacts(
    *,
    activity_snapshot: Mapping[str, object],
    result: Mapping[str, object],
    require_commit_message: bool,
) -> dict[str, object]:
    """Dispatch one frozen Harness result to its normalizing adapter."""

    harness = activity_snapshot.get('harness')
    if isinstance(harness, Mapping) and harness.get('kind') in (
        'codex_cli', 'copilot_cli'
    ):
        return cli_runtime_artifacts(
            activity_snapshot=activity_snapshot,
            result=result,
            require_commit_message=require_commit_message,
        )
    raise RuntimeError('Activity snapshot selects an unsupported Harness.')


def cli_runtime_artifacts(
    *,
    activity_snapshot: Mapping[str, object],
    result: Mapping[str, object],
    require_commit_message: bool,
) -> dict[str, object]:
    """Validate and normalize the complete CLI Harness observation."""

    harness = activity_snapshot.get('harness')
    if not isinstance(harness, Mapping) or (
        harness.get('kind') not in ('codex_cli', 'copilot_cli')
        or harness.get('version') != 'v1'
        or harness.get('config') != {}
    ):
        raise RuntimeError('Activity snapshot has an invalid CLI Harness.')
    schema_version = result.get('schema_version', 'v1')
    if schema_version != 'v1':
        raise ActivityRunValidationError(
            field_name='result.schema_version',
            message='must be v1',
        )
    reported_harness = result.get('harness')
    if reported_harness is not None and reported_harness != harness:
        raise ActivityRunValidationError(
            field_name='result.harness',
            message='must match the frozen Harness',
        )
    expected_model = activity_snapshot.get('requested_model')
    requested_model = result.get('requested_model')
    actual_model = result.get('actual_model')
    if not isinstance(expected_model, str) or not expected_model.strip():
        raise RuntimeError('CLI Activity snapshot is missing requested_model.')
    completed = result.get('completed') is True
    if requested_model is not None and requested_model != expected_model:
        raise ActivityRunValidationError(
            field_name='result.requested_model',
            message='must match the frozen requested model',
        )
    if completed and requested_model != expected_model:
        raise ActivityRunValidationError(
            field_name='result.requested_model',
            message='must match the frozen requested model',
        )
    if completed and (
        not isinstance(actual_model, str) or not actual_model.strip()
    ):
        raise ActivityRunValidationError(
            field_name='result.actual_model',
            message='must not be empty',
        )
    artifacts: dict[str, object] = {
        'schema_version': 'v1',
        'harness': dict(harness),
        'completed': completed,
        'started_at': result.get('started_at'),
        'completed_at': result.get('completed_at'),
        'duration_ms': result.get('duration_ms'),
        'requested_model': requested_model or expected_model,
        'actual_model': actual_model,
        'reasoning_effort': result.get('reasoning_effort'),
        'session_reference': result.get('session_reference'),
        'usage': dict(result.get('usage', {})),
        'exit_code': result.get('exit_code'),
        'diagnostics': list(result.get('diagnostics', [])),
        'materialized_skills': list(result.get('materialized_skills', [])),
        'source_commit_sha': result.get('source_commit_sha'),
        'final_commit_sha': result.get('final_commit_sha'),
        'final_diff': result.get('final_diff', ''),
        'changed_files': list(result.get('changed_files', [])),
        'final_response': result.get('final_response', ''),
        'error': result.get('error'),
    }
    for key in ('turn_id', 'phase', 'agent_id', 'role', 'iteration'):
        if result.get(key) is not None:
            artifacts[key] = result[key]
    output = result.get('output')
    if isinstance(output, Mapping) and output:
        artifacts['output'] = dict(output)
    if require_commit_message and completed:
        commit_message = result.get('commit_message')
        if not isinstance(commit_message, str) or not commit_message.strip():
            raise ActivityRunValidationError(
                field_name='result.commit_message',
                message='must not be empty',
            )
        artifacts['commit_message'] = commit_message
    return artifacts


def with_cli_commit_result(
    *,
    artifacts: Mapping[str, object],
    result: Mapping[str, object],
) -> dict[str, object]:
    """Complete CLI Harness observability with the authorized Git outcome."""

    updated = dict(artifacts)
    committed = result.get('committed') is True
    updated['committed'] = committed
    commit_sha = result.get('commit_sha')
    if committed and isinstance(commit_sha, str) and commit_sha.strip():
        updated['final_commit_sha'] = commit_sha
    commit_error = result.get('error')
    if isinstance(commit_error, str) and commit_error.strip():
        updated['commit_error'] = commit_error
    return updated
