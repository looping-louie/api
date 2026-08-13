"""Persistence contract for loop execution records."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence

from src.app.models.loop_run import LoopRunDocument


class LoopRunRepository(Protocol):
    """Persistence operations required by the loop-run service."""

    async def has_runs(
        self,
        *,
        workspace_id: str,
        loop_id: str,
    ) -> bool:
        """Return whether a loop has retained execution history."""
        raise NotImplementedError

    async def create(self, *, document: LoopRunDocument) -> LoopRunDocument:
        """Persist one newly created loop run."""
        raise NotImplementedError

    async def get(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        run_id: str,
    ) -> LoopRunDocument | None:
        """Return one loop run within its parent loop."""
        raise NotImplementedError

    async def get_for_activity(
        self,
        *,
        workspace_id: str,
        activity_id: str,
        run_id: str,
    ) -> LoopRunDocument | None:
        """Return one loop run within its parent activity."""
        raise NotImplementedError

    async def list(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[LoopRunDocument], int]:
        """Return one page of loop runs and its unpaginated total."""
        raise NotImplementedError

    async def list_for_activity(
        self,
        *,
        workspace_id: str,
        activity_id: str,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[LoopRunDocument], int]:
        """Return one page of runs and its total for an activity."""
        raise NotImplementedError

    async def continue_collect_snapshot(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        run_id: str,
        continuation_token: str,
        idempotency_key: str,
        execution_context: dict[str, object],
        updated_at: datetime,
    ) -> LoopRunDocument:
        """Persist the legacy snapshot-only checkpoint transition."""
        raise NotImplementedError

    async def transition(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        run_id: str,
        continuation_token: str,
        idempotency_key: str,
        expected_action: str,
        status: str,
        state: str,
        next_action: str,
        next_continuation_token: str | None,
        execution_context: dict[str, object],
        updated_at: datetime,
        iteration: int | None = None,
    ) -> LoopRunDocument:
        """Persist one validated checkpoint transition or return its replay."""
        raise NotImplementedError

    async def transition_for_activity(
        self,
        *,
        workspace_id: str,
        activity_id: str,
        run_id: str,
        continuation_token: str,
        idempotency_key: str,
        expected_action: str,
        status: str,
        state: str,
        next_action: str,
        next_continuation_token: str | None,
        execution_context: dict[str, object],
        updated_at: datetime,
        iteration: int | None = None,
    ) -> LoopRunDocument:
        """Persist one validated activity-owned checkpoint transition."""
        raise NotImplementedError
