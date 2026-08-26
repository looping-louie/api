"""Factories for pipeline service and persistence tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from src.app.models.pipeline import (
    PipelineActivityStep,
    PipelineDocument,
)


BASE_TIME = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)


def build_pipeline(
    *,
    pipeline_id: str = "pipeline-1",
    status: str = "active",
) -> PipelineDocument:
    """Build one complete two-step pipeline."""

    return PipelineDocument(
        id=pipeline_id,
        name=f"Pipeline {pipeline_id}",
        description="Run and approve.",
        status=status,  # type: ignore[arg-type]
        steps=(
            PipelineActivityStep(activity_id="activity-1"),
            PipelineActivityStep(activity_id="activity-2"),
        ),
        created_at=BASE_TIME,
        created_by="user-1",
        updated_at=BASE_TIME,
        updated_by="user-1",
    )


def with_status(
    document: PipelineDocument,
    status: str,
) -> PipelineDocument:
    """Return a pipeline copy in another persisted status."""

    return replace(document, status=status)  # type: ignore[arg-type]
