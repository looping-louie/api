"""Tests for API server logging configuration."""

from __future__ import annotations

import json
import re
from pathlib import Path

from uvicorn.logging import AccessFormatter


LOGGING_CONFIG_PATH = Path(__file__).parents[2] / 'config' / 'uvicorn-logging.json'


def test_access_logs_include_an_iso_timestamp() -> None:
    """Access log formatting starts each request with a timezone-aware timestamp."""

    configuration = json.loads(LOGGING_CONFIG_PATH.read_text(encoding='utf-8'))
    formatter_config = configuration['formatters']['access']
    formatter = AccessFormatter(
        fmt=formatter_config['format'],
        datefmt=formatter_config['datefmt'],
        use_colors=False,
    )
    record = _access_record()

    formatted = formatter.format(record)

    assert re.match(
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4} \| INFO:',
        formatted,
    )
    assert '127.0.0.1 - "GET /api/v1/pipeline-runs?offset=0 HTTP/1.1" 200 OK' in formatted


def _access_record():
    """Create one representative Uvicorn access record."""

    import logging

    return logging.LogRecord(
        name='uvicorn.access',
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=('127.0.0.1', 'GET', '/api/v1/pipeline-runs?offset=0', '1.1', 200),
        exc_info=None,
    )
