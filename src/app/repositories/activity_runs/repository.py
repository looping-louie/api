"""Persistence contract for activity execution records."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence

from src.app.models.activity_run import ActivityRunDocument


class ActivityRunRepository(Protocol):
    """Persistence operations required by the activity-run service."""

    async def create(
        self,
        *,
        document: ActivityRunDocument,
    ) -> ActivityRunDocument:
        """Persist one initial activity execution."""
        raise NotImplementedError

    async def get(
        self,
        *,
        workspace_id: str,
        activity_id: str,
        run_id: str,
    ) -> ActivityRunDocument | None:
        """Return one run within its owning activity."""
        raise NotImplementedError

    async def list(
        self,
        *,
        workspace_id: str,
        activity_id: str,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[ActivityRunDocument], int]:
        """Return one activity-run page and its unpaginated total."""
        raise NotImplementedError

    async def has_active_pipeline_lease(
        self,
        *,
        workspace_id: str,
        activity_run_id: str,
        pipeline_run_id: str | None,
        lease_token: str | None,
        now: datetime,
    ) -> bool:
        """Return whether a Pipeline child has a valid current worker lease."""
        raise NotImplementedError

    async def transition(
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
        pipeline_run_id: str | None = None,
        lease_token: str | None = None,
    ) -> ActivityRunDocument:
        """Persist one fenced checkpoint transition or return its replay."""
        raise NotImplementedError
