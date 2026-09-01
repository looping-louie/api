"""Shared readers for frozen Pipeline execution graphs."""

from typing import Mapping


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
