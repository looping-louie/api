"""Helpers for persisted loop-run operation contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


ALLOWED_OPERATIONS = {'create', 'replace', 'replace_text', 'delete'}


def parse_file_operations(
    raw: str,
    *,
    require_non_empty: bool = False,
) -> list[dict]:
    """Parse and validate generator output operations."""
    cleaned = _extract_json_object(raw)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON from generator: {exc}') from exc
    if not isinstance(data, dict):
        raise ValueError('Generator JSON must be an object')

    if 'operation' in data:
        data = {'operations': [data]}

    operations = data.get('operations')

    if operations is None:
        operations = _file_entries_as_create_operations(data)

    if not isinstance(operations, list):
        raise ValueError('Generator JSON must contain an operations list')
    if require_non_empty and not operations:
        raise ValueError('Generator JSON must contain at least one operation')

    for operation in operations:
        _normalize_replace_text_aliases(operation)
        _validate_operation(operation)

    return operations


def _normalize_replace_text_aliases(operation: object) -> None:
    """Map common model aliases to the CLI replace-text operation contract."""

    if not isinstance(operation, dict) or operation.get('operation') != 'replace_text':
        return

    for alias, field_name in (
        ('old_text', 'old_content'),
        ('new_text', 'new_content'),
    ):
        if alias not in operation:
            continue
        alias_value = operation.pop(alias)
        if field_name in operation and operation[field_name] != alias_value:
            raise ValueError(f'{alias} conflicts with {field_name}')
        operation[field_name] = alias_value


def _file_entries_as_create_operations(
    data: Mapping[str, object],
) -> list[dict[str, str]] | None:
    """Normalize the observed model file-list response into create operations."""

    files = data.get('files')
    if not isinstance(files, list):
        return None

    operations: list[dict[str, str]] = []
    for file_entry in files:
        if not isinstance(file_entry, Mapping):
            return None
        name = file_entry.get('name')
        content = file_entry.get('content')
        if not isinstance(name, str) or not isinstance(content, str):
            return None
        operations.append(
            {
                'operation': 'create',
                'path': name,
                'content': content,
            }
        )
    return operations


def _extract_json_object(raw: str) -> str:
    """Extract the first JSON object from raw model output."""
    text = raw.strip()

    if text.startswith('```'):
        lines = text.splitlines()
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].startswith('```'):
            lines = lines[:-1]
        text = '\n'.join(lines).strip()

    start = text.find('{')
    end = text.rfind('}')

    if start == -1 or end == -1 or end <= start:
        raise ValueError('Generator output does not contain a JSON object')

    return text[start : end + 1]


def _validate_operation(operation: dict) -> None:
    """Validate one file operation object."""
    if not isinstance(operation, dict):
        raise ValueError('Each operation must be an object')

    op = operation.get('operation')
    path = operation.get('path')

    if op not in ALLOWED_OPERATIONS:
        raise ValueError(f'Invalid operation: {op}')

    if not path or not isinstance(path, str):
        raise ValueError('Operation path must be a non-empty string')

    if path.startswith('/'):
        raise ValueError(f'Absolute paths are not allowed: {path}')

    if '..' in Path(path).parts:
        raise ValueError(f'Parent path traversal is not allowed: {path}')

    if op in {'create', 'replace'}:
        content = operation.get('content')
        if not isinstance(content, str):
            raise ValueError(f'{op} operation requires string content')

    if op == 'delete' and any(
        key in operation
        for key in ('content', 'old_content', 'new_content')
    ):
        raise ValueError(
            'delete operation must not include file content'
        )

    if op == 'replace_text':
        old_content = operation.get('old_content')
        new_content = operation.get('new_content')

        if not isinstance(old_content, str) or not old_content:
            raise ValueError(
                'replace_text operation requires non-empty old_content'
            )

        if not isinstance(new_content, str):
            raise ValueError(
                'replace_text operation requires string new_content'
            )

        if 'content' in operation:
            raise ValueError(
                'replace_text operation must not include content'
            )
