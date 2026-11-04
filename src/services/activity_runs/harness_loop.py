"""Coordinate multi-agent loops as persisted Harness turns."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HarnessLoopAdvance:
    """State selected after accepting one normalized Harness observation."""

    context: dict[str, object]
    terminal: bool = False
    failed: bool = False


def start_harness_loop(
    *,
    snapshot: Mapping[str, object],
    context: Mapping[str, object],
    iteration: int,
) -> dict[str, object]:
    """Schedule the first turn for a frozen direct, refinement, or roundtable loop."""

    flow = str(snapshot.get('flow'))
    agents = _agents(snapshot)
    state: dict[str, object] = {
        'flow': flow,
        'turns': [],
        'proposals': [],
        'reviews': [],
    }
    phase = 'proposal' if flow == 'roundtable' else 'execute'
    candidates = _role_agents(agents, 'generator')
    return _schedule(
        context={**dict(context), 'harness_loop': state},
        agent=candidates[0],
        phase=phase,
        iteration=iteration,
        index=0,
    )


def advance_harness_loop(
    *,
    snapshot: Mapping[str, object],
    context: Mapping[str, object],
    artifacts: Mapping[str, object],
    iteration: int,
) -> HarnessLoopAdvance:
    """Persist one turn and schedule the next semantic loop checkpoint."""

    pending = _mapping(context.get('pending_harness_turn'), 'pending Harness turn')
    _require_matching_turn(pending, artifacts)
    state = dict(_mapping(context.get('harness_loop'), 'Harness loop state'))
    turns = list(_sequence(state.get('turns')))
    turns.append(dict(artifacts))
    state['turns'] = turns
    updated = {**dict(context), 'harness_loop': state}
    updated.pop('pending_harness_turn', None)
    if artifacts.get('completed') is not True:
        updated['runtime_artifacts'] = dict(artifacts)
        return HarnessLoopAdvance(updated, terminal=True, failed=True)

    phase = str(pending.get('phase'))
    if phase == 'proposal':
        return _after_proposal(snapshot, updated, state, artifacts, iteration)
    if phase in ('execute', 'aggregate'):
        updated['runtime_artifacts'] = dict(artifacts)
        if snapshot.get('flow') != 'refinement':
            return HarnessLoopAdvance(updated, terminal=True)
        reviewers = _role_agents(_agents(snapshot), 'reviewer')
        return HarnessLoopAdvance(_schedule(
            context=updated,
            agent=reviewers[0],
            phase='review',
            iteration=iteration,
            index=0,
            final_diff=str(artifacts.get('final_diff', '')),
        ))
    if phase == 'review':
        return _after_review(snapshot, updated, state, artifacts, iteration)
    raise ValueError(f'Unsupported Harness turn phase: {phase}.')


def pending_harness_payload(context: Mapping[str, object]) -> dict[str, object]:
    """Expose the current immutable turn plus compatibility routing fields."""

    turn = dict(_mapping(context.get('pending_harness_turn'), 'pending Harness turn'))
    return {
        'turn': turn,
        'requested_model': turn['requested_model'],
        'instruction_snapshot': turn['instruction_snapshot'],
    }


def _after_proposal(
    snapshot: Mapping[str, object],
    context: dict[str, object],
    state: dict[str, object],
    artifacts: Mapping[str, object],
    iteration: int,
) -> HarnessLoopAdvance:
    """Collect one read-only proposal and select the next participant."""

    proposals = list(_sequence(state.get('proposals')))
    proposals.append(_turn_output(artifacts, 'proposal'))
    state['proposals'] = proposals
    generators = _role_agents(_agents(snapshot), 'generator')
    if len(proposals) < len(generators):
        return HarnessLoopAdvance(_schedule(
            context=context,
            agent=generators[len(proposals)],
            phase='proposal',
            iteration=iteration,
            index=len(proposals),
        ))
    aggregator = _role_agents(_agents(snapshot), 'aggregator')[0]
    return HarnessLoopAdvance(_schedule(
        context=context,
        agent=aggregator,
        phase='aggregate',
        iteration=iteration,
        index=0,
        proposals=proposals,
    ))


def _after_review(
    snapshot: Mapping[str, object],
    context: dict[str, object],
    state: dict[str, object],
    artifacts: Mapping[str, object],
    iteration: int,
) -> HarnessLoopAdvance:
    """Collect reviews, then approve the writer result or schedule a retry."""

    reviews = list(_sequence(state.get('reviews')))
    review = _turn_output(artifacts, 'review')
    reviews.append(review)
    state['reviews'] = reviews
    reviewers = _role_agents(_agents(snapshot), 'reviewer')
    writer = _mapping(context.get('runtime_artifacts'), 'writer artifacts')
    if len(reviews) < len(reviewers):
        return HarnessLoopAdvance(_schedule(
            context=context,
            agent=reviewers[len(reviews)],
            phase='review',
            iteration=iteration,
            index=len(reviews),
            final_diff=str(writer.get('final_diff', '')),
        ))
    if all(item.get('approved') is True for item in reviews):
        return HarnessLoopAdvance(context, terminal=True)
    if iteration >= _max_iterations(snapshot):
        context['failure'] = {
            'source': 'harness_loop',
            'type': 'review_rejected',
            'message': 'Reviewers rejected the result at the iteration limit.',
        }
        return HarnessLoopAdvance(context, terminal=True, failed=True)
    state['reviews'] = []
    generator = _role_agents(_agents(snapshot), 'generator')[0]
    feedback = [
        str(item.get('feedback', '')).strip()
        for item in reviews
        if str(item.get('feedback', '')).strip()
    ]
    return HarnessLoopAdvance(_schedule(
        context=context,
        agent=generator,
        phase='execute',
        iteration=iteration + 1,
        index=0,
        feedback=feedback,
    ))


def _schedule(
    *,
    context: Mapping[str, object],
    agent: Mapping[str, object],
    phase: str,
    iteration: int,
    index: int,
    **inputs: object,
) -> dict[str, object]:
    """Attach one deterministic Harness turn to the persisted execution context."""

    agent_id = str(agent.get('id') or agent.get('persona_id') or f'{agent.get("role")}-{index + 1}')
    turn = {
        'id': f'{iteration}:{phase}:{agent_id}',
        'phase': phase,
        'iteration': iteration,
        'agent_id': agent_id,
        'role': agent.get('role'),
        'requested_model': agent.get('requested_model'),
        'instruction_snapshot': agent.get('instruction_snapshot'),
        'workspace_access': 'read_only' if phase in ('proposal', 'review') else 'workspace_write',
        **inputs,
    }
    return {**dict(context), 'pending_harness_turn': turn}


def _require_matching_turn(
    pending: Mapping[str, object],
    artifacts: Mapping[str, object],
) -> None:
    """Reject observations that do not belong to the leased pending turn."""

    for key in ('turn_id', 'phase', 'agent_id', 'iteration'):
        expected_key = 'id' if key == 'turn_id' else key
        reported = artifacts.get(key)
        if reported != pending.get(expected_key):
            raise ValueError(f'Harness result {key} does not match the pending turn.')


def _turn_output(artifacts: Mapping[str, object], kind: str) -> dict[str, object]:
    """Return one structured proposal or review from a normalized observation."""

    output = artifacts.get('output')
    if not isinstance(output, Mapping):
        raise ValueError(f'Harness {kind} turn is missing structured output.')
    return dict(output)


def _agents(snapshot: Mapping[str, object]) -> list[Mapping[str, object]]:
    """Return the validated frozen agents from an Activity snapshot."""

    agents = snapshot.get('agents')
    if not isinstance(agents, Sequence) or isinstance(agents, (str, bytes)):
        raise ValueError('Harness loop snapshot is missing agents.')
    return [agent for agent in agents if isinstance(agent, Mapping)]


def _role_agents(
    agents: Sequence[Mapping[str, object]],
    role: str,
) -> list[Mapping[str, object]]:
    """Return agents assigned to one semantic loop role."""

    selected = [agent for agent in agents if agent.get('role') == role]
    if not selected:
        raise ValueError(f'Harness loop is missing a {role} agent.')
    return selected


def _mapping(value: object, label: str) -> Mapping[str, object]:
    """Require one mapping from persisted untyped execution context."""

    if not isinstance(value, Mapping):
        raise ValueError(f'Activity context is missing its {label}.')
    return value


def _sequence(value: object) -> Sequence[object]:
    """Return a persisted list value or an empty sequence."""

    return value if isinstance(value, list) else ()


def _max_iterations(snapshot: Mapping[str, object]) -> int:
    """Return the frozen refinement iteration limit."""

    conditions = snapshot.get('stop_conditions')
    value = conditions.get('max_iterations') if isinstance(conditions, Mapping) else None
    return value if isinstance(value, int) else 1
