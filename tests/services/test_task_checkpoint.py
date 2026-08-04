"""Tests for parsing model-generated checkpoint operations."""

import json

from src.app.services.task_checkpoint import parse_file_operations


def test_parse_file_operations_normalizes_model_file_entries() -> None:
    """A model file list becomes a validated create-operation plan."""

    operations = parse_file_operations(
        json.dumps(
            {
                'files': [
                    {
                        'name': 'ideas.md',
                        'content': '# Product brief\n',
                    },
                ],
            },
        ),
    )

    assert operations == [
        {
            'operation': 'create',
            'path': 'ideas.md',
            'content': '# Product brief\n',
        },
    ]