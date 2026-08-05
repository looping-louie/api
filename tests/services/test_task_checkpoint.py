"""Tests for parsing model-generated checkpoint operations."""

import json

import pytest

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


def test_parse_file_operations_rejects_empty_operations() -> None:
    """A successful generator plan must request at least one file change."""

    with pytest.raises(ValueError, match='at least one operation'):
        parse_file_operations(
            '{"operations": []}',
            require_non_empty=True,
        )
