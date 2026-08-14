"""Tests for pure loop-run input validation."""

import pytest

from src.app.services.loops.types import LoopValidationError
from src.app.services.loop_runs.validation import require_text


def test_require_text_returns_trimmed_value() -> None:
    """Normalize surrounding whitespace before accepting input."""

    assert require_text('  loop-run-1  ', 'run_id') == 'loop-run-1'


def test_require_text_rejects_blank_value() -> None:
    """Reject whitespace-only input with the existing loop error contract."""

    with pytest.raises(LoopValidationError, match="Invalid loop field 'run_id'"):
        require_text('  ', 'run_id')
