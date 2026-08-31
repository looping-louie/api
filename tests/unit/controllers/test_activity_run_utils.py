"""Tests for ActivityRun HTTP response translation."""

from datetime import UTC, datetime
from typing import cast

from src.app.controllers.activity_runs.utils import activity_run_response
from src.app.models.activity_run import ActivityRunDocument


def test_run_harness_payload_exposes_frozen_instruction_snapshot() -> None:
    """A runtime receives the exact Persona and Skills frozen by PipelineRun."""

    now = datetime(2026, 8, 31, tzinfo=UTC)
    instruction_snapshot = {
        'snapshot_version': 1,
        'persona': {'id': 'persona-1', 'content': 'Act as an implementer.'},
        'skills': [{'id': 'skill-1', 'content': 'Preserve API contracts.'}],
    }
    document = ActivityRunDocument(
        id='run-1', project_id='project-1', activity_id='activity-1',
        input='Implement.', status='in_progress',
        state=cast(object, 'awaiting_harness'),
        next_action=cast(object, 'run_harness'), iteration=1, token_revision=1,
        continuation_token='token-1',
        activity_snapshot={
            'harness': {'kind': 'codex_cli', 'version': 'v1', 'config': {}},
            'instruction_snapshot': instruction_snapshot,
        },
        execution_context={
            'repo_context': 'Python project.',
            'constitution': 'Keep tests green.',
            'project_profile': {},
        },
        created_at=now, created_by='user-1', updated_at=now,
    )

    response = activity_run_response(document)

    assert response.payload['instruction_snapshot'] == instruction_snapshot
