"""Persistence contract for durable pipeline execution records."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.app.models.activity_run import ActivityRunDocument
from src.app.models.pipeline_run import (
    PipelineRunDocument,
    PipelineRunEventDocument,
)


class PipelineRunRepository(Protocol):
    """Store pipeline-run state and selected child activity runs atomically."""

    async def list(
        self,
        *,
        project_id: str,
        offset: int,
        limit: int,
        pipeline_id: str | None,
        status: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> tuple[list[PipelineRunDocument], int]:
        """Return one filtered Project page and its total."""
        raise NotImplementedError

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
        project_id: str,
        pipeline_id: str,
        run_id: str,
    ) -> PipelineRunDocument | None:
        """Return one pipeline run under its owning pipeline."""
        raise NotImplementedError

    async def start(
        self,
        *,
        document: PipelineRunDocument,
        expected_updated_at: datetime,
        activity_run: ActivityRunDocument | None,
    ) -> bool:
        """Start a prepared run and optionally persist its human child."""
        raise NotImplementedError

    async def list_claimable(
        self,
        *,
        project_id: str,
        pipeline_id: str,
        claimed_before: datetime,
    ) -> list[PipelineRunDocument]:
        """Return queued or lease-expired runs under one Pipeline."""
        raise NotImplementedError

    async def claim(
        self,
        *,
        document: PipelineRunDocument,
        expected_updated_at: datetime,
        expected_current_activity_run_id: str | None,
        activity_run: ActivityRunDocument | None,
    ) -> bool:
        """Atomically assign a worker lease and optionally create a child run."""
        raise NotImplementedError

    async def renew_lease(
        self,
        *,
        document: PipelineRunDocument,
        expected_lease_token: str | None,
        now: datetime,
    ) -> bool:
        """Extend an active worker lease only when its token still matches."""
        raise NotImplementedError

    async def transition(
        self,
        *,
        document: PipelineRunDocument,
        expected_current_activity_run_id: str | None,
        expected_lease_token: str,
        now: datetime,
        activity_run: ActivityRunDocument | None,
    ) -> bool:
        """Atomically replace a run after confirming its current child."""
        raise NotImplementedError

    async def list_events(
        self,
        *,
        project_id: str,
        pipeline_id: str,
        run_id: str,
    ) -> list[PipelineRunEventDocument]:
        """Return immutable events for one scoped Pipeline run."""
        raise NotImplementedError
