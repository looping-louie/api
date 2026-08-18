"""Application contracts and errors for loop-run operations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime


Clock = Callable[[], datetime]
"""Callable that supplies the current timestamp."""

IdFactory = Callable[[], str]
"""Callable that supplies a persisted loop-run identifier."""

TokenFactory = Callable[[], str]
"""Callable that supplies a loop-run continuation token."""


class LoopRunNotFoundError(Exception):
    """Raised when a loop run is absent from its parent loop."""

    def __init__(self, *, loop_id: str, run_id: str) -> None:
        """Store the parent loop and missing run identifiers."""

        super().__init__(f"Loop run '{run_id}' was not found for loop '{loop_id}'.")
        self.loop_id = loop_id
        self.run_id = run_id


class LoopRunUnavailableError(Exception):
    """Raised when a loop cannot start a new execution."""

    def __init__(self, *, loop_id: str, loop_status: str) -> None:
        """Store the loop state that prevents execution."""

        super().__init__(f"Loop '{loop_id}' with status '{loop_status}' cannot run.")
        self.loop_id = loop_id
        self.loop_status = loop_status
