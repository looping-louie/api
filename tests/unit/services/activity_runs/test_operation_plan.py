"""Tests for parsing model-generated ActivityRun operation plans."""

import json

import pytest

from src.app.services.activity_runs.operation_plan import parse_file_operations


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


def test_parse_file_operations_normalizes_single_replace_text_aliases() -> None:
    """A standalone model operation uses the CLI replace-text field names."""

    operations = parse_file_operations(
        json.dumps(
            {
                'operation': 'replace_text',
                'path': 'index.html',
                'old_text': 'Old text',
                'new_text': 'New text',
            },
        ),
    )

    assert operations == [
        {
            'operation': 'replace_text',
            'path': 'index.html',
            'old_content': 'Old text',
            'new_content': 'New text',
        },
    ]


def test_parse_file_operations_rejects_empty_operations() -> None:
    """A successful generator plan must request at least one file change."""

    with pytest.raises(ValueError, match='at least one operation'):
        parse_file_operations(
            '{"operations": []}',
            require_non_empty=True,
        )