"""Factories for pipeline service and persistence tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from src.app.models.loop import (
    LoopAgent,
    LoopDocument,
    LoopOutputContract,
    LoopStopConditions,
)
from src.app.models.pipeline import (
    PipelineDocument,
    PipelineHumanGateStep,
    PipelineLoopStep,
)


BASE_TIME = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)


def build_loop(
    *,
    loop_id: str = "loop-1",
    workspace_id: str = "workspace-1",
    status: str = "active",
) -> LoopDocument:
    """Build one complete loop suitable for pipeline references."""

    return LoopDocument(
        id=loop_id,
        workspace_id=workspace_id,
        title=f"Loop {loop_id}",
        description="Produce one answer.",
        flow="direct",
        status=status,  # type: ignore[arg-type]
        stop_conditions=LoopStopConditions(max_iterations=3),
        agents=(
            LoopAgent(
                id=f"{loop_id}-agent",
                model_id="model-1",
                persona_id="persona-1",
                role="generator",
            ),
        ),
        output_contract=LoopOutputContract(
            type="text",
            description="Answer.",
            files=(),
            schema=None,
        ),
        created_at=BASE_TIME,
        created_by="user-1",
        updated_at=BASE_TIME,
        updated_by="user-1",
    )


def build_pipeline(
    *,
    pipeline_id: str = "pipeline-1",
    workspace_id: str = "workspace-1",
    status: str = "active",
) -> PipelineDocument:
    """Build one complete two-step pipeline."""

    return PipelineDocument(
        id=pipeline_id,
        workspace_id=workspace_id,
        title=f"Pipeline {pipeline_id}",
        description="Run and approve.",
        status=status,  # type: ignore[arg-type]
        steps=(
            PipelineLoopStep(type="loop", loop_id="loop-1"),
            PipelineHumanGateStep(
                type="human_gate",
                gate_type="approval",
                config=None,
            ),
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
