"""Shared readers for frozen Pipeline execution graphs."""

from collections.abc import Mapping, Sequence

from src.app.models.pipeline_run import PipelineRunStepDocument


def snapshot_dependencies(
    snapshot: Mapping[str, object],
) -> dict[str, list[dict[str, str]]]:
    """Return dependency requirements in persisted Pipeline status terms."""

    values = snapshot.get('steps')
    if not isinstance(values, list):
        raise RuntimeError('Pipeline run snapshot is invalid.')
    return {
        str(step['activity_id']): [
            {
                'activity_id': str(item['activity_id']),
                'condition': 'completed' if item['condition'] == 'success' else 'failed',
            }
            for item in step['depends_on']
        ]
        for step in values
        if isinstance(step, dict)
    }


def first_dependency_ready_step(
    steps: Sequence[PipelineRunStepDocument],
    dependencies: Mapping[str, list[dict[str, str]]],
) -> PipelineRunStepDocument | None:
    """Return the first pending step whose frozen dependencies are satisfied."""

    by_activity_id = {step.activity_id: step for step in steps}
    return next(
        (
            step for step in steps
            if step.status == 'pending'
            and all(
                by_activity_id[item['activity_id']].status == item['condition']
                for item in dependencies[step.activity_id]
            )
        ),
        None,
    )
