"""Persistence contract for durable pipeline execution records."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.app.models.activity_run import ActivityRunDocument
from src.app.models.pipeline_run import PipelineRunDocument


class PipelineRunRepository(Protocol):
    """Store pipeline-run state and selected child activity runs atomically."""

    async def create(
        self,
        *,
        document: PipelineRunDocument,
        activity_run: ActivityRunDocument | None,
    ) -> PipelineRunDocument:
        """Persist a pipeline run and optionally create a child run."""
        raise NotImplementedError

    async def get(
        self,
        *,
        workspace_id: str,
        pipeline_id: str,
        run_id: str,
    ) -> PipelineRunDocument | None:
        """Return one pipeline run under its owning pipeline."""
        raise NotImplementedError

    async def find_claimable(
        self,
        *,
        workspace_id: str,
        claimed_before: datetime,
    ) -> PipelineRunDocument | None:
        """Return one queued or lease-expired pipeline run in a workspace."""
        raise NotImplementedError

    async def claim(
        self,
        *,
        document: PipelineRunDocument,
        expected_updated_at: datetime,
        activity_run: ActivityRunDocument | None,
    ) -> bool:
        """Atomically assign a worker lease and optionally create a child run."""
        raise NotImplementedError

    async def renew_lease(
        self,
        *,
        document: PipelineRunDocument,
        expected_lease_token: str,
        now: datetime,
    ) -> bool:
        """Extend an active worker lease only when its token still matches."""
        raise NotImplementedError

    async def transition(
        self,
        *,
        document: PipelineRunDocument,
        expected_current_activity_run_id: str | None,
        activity_run: ActivityRunDocument | None,
    ) -> bool:
        """Atomically replace a run after confirming its current child."""
        raise NotImplementedError
