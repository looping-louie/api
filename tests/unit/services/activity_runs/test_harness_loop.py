"""Tests for API-owned multi-agent Harness loop coordination."""

from src.app.services.activity_runs.harness_loop import (
    advance_harness_loop,
    pending_harness_payload,
    start_harness_loop,
)


def test_refinement_runs_writer_reviewers_and_retry_in_order() -> None:
    """Rejected review feedback schedules the same writer at the next iteration."""

    snapshot = _snapshot('refinement', ('generator', 'reviewer', 'reviewer'))
    context = start_harness_loop(snapshot=snapshot, context={}, iteration=1)
    assert pending_harness_payload(context)['requested_model'] == 'model-generator-1'

    writer = advance_harness_loop(
        snapshot=snapshot, context=context,
        artifacts=_result(context, final_diff='diff'), iteration=1,
    )
    assert writer.context['pending_harness_turn']['phase'] == 'review'

    first_review = advance_harness_loop(
        snapshot=snapshot, context=writer.context,
        artifacts=_result(writer.context, output={
            'approved': False, 'feedback': 'Add tests.',
        }),
        iteration=1,
    )
    assert first_review.context['pending_harness_turn']['agent_id'] == 'reviewer-3'

    retry = advance_harness_loop(
        snapshot=snapshot, context=first_review.context,
        artifacts=_result(first_review.context, output={
            'approved': True, 'feedback': '',
        }),
        iteration=1,
    )
    turn = retry.context['pending_harness_turn']
    assert turn['phase'] == 'execute'
    assert turn['iteration'] == 2
    assert turn['feedback'] == ['Add tests.']
    assert len(retry.context['harness_loop']['turns']) == 3


def test_roundtable_runs_all_proposals_before_the_aggregator() -> None:
    """Read-only proposals are supplied together to the single writer turn."""

    snapshot = _snapshot('roundtable', ('generator', 'generator', 'aggregator'))
    context = start_harness_loop(snapshot=snapshot, context={}, iteration=1)

    first = advance_harness_loop(
        snapshot=snapshot, context=context,
        artifacts=_result(context, output={'proposal': 'Proposal A'}), iteration=1,
    )
    assert first.context['pending_harness_turn']['agent_id'] == 'generator-2'
    second = advance_harness_loop(
        snapshot=snapshot, context=first.context,
        artifacts=_result(first.context, output={'proposal': 'Proposal B'}), iteration=1,
    )
    turn = second.context['pending_harness_turn']
    assert turn['phase'] == 'aggregate'
    assert turn['workspace_access'] == 'workspace_write'
    assert turn['proposals'] == [
        {'proposal': 'Proposal A'}, {'proposal': 'Proposal B'},
    ]

    completed = advance_harness_loop(
        snapshot=snapshot, context=second.context,
        artifacts=_result(second.context, final_diff='diff'), iteration=1,
    )
    assert completed.terminal is True
    assert completed.failed is False
    assert completed.context['runtime_artifacts']['agent_id'] == 'aggregator-3'


def _snapshot(flow: str, roles: tuple[str, ...]) -> dict[str, object]:
    """Build one frozen Activity snapshot with distinct agent models."""

    return {
        'flow': flow,
        'stop_conditions': {'max_iterations': 3},
        'agents': [
            {
                'id': f'{role}-{index}',
                'role': role,
                'requested_model': f'model-{role}-{index}',
                'instruction_snapshot': {'persona': {'id': f'persona-{index}'}},
            }
            for index, role in enumerate(roles, 1)
        ],
    }


def _result(
    context: dict[str, object],
    *,
    output: dict[str, object] | None = None,
    final_diff: str = '',
) -> dict[str, object]:
    """Build a matching normalized Harness observation for the pending turn."""

    turn = context['pending_harness_turn']
    return {
        'completed': True,
        'turn_id': turn['id'],
        'phase': turn['phase'],
        'agent_id': turn['agent_id'],
        'role': turn['role'],
        'iteration': turn['iteration'],
        'output': output or {},
        'final_diff': final_diff,
    }
