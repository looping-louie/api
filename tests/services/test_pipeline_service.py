"""Unit tests for pipeline application behavior."""

from __future__ import annotations

from itertools import count

import pytest

from src.app.models.pipeline import PipelineHumanGateStep
from src.app.services.loop_types import LoopNotFoundError
from src.app.services.pipeline_service import PipelineService
from src.app.services.pipeline_types import (
    InvalidPipelineStepsError,
    PipelineArchivedError,
    PipelineCreate,
    PipelinePatch,
    PipelineQuizConfigInput,
    PipelineStepInput,
)
from src.app.services.shared.tenant_service import TenantService
from tests.conftest import IncrementingClock
from tests.factories.pipelines import build_loop
from tests.fakes.loop_repository import FakeLoopRepository
from tests.fakes.pipeline_repository import FakePipelineRepository


def loop_step(loop_id: str = "loop-1") -> PipelineStepInput:
    """Build one loop-reference input."""

    return PipelineStepInput(type="loop", loop_id=loop_id)


def approval_step() -> PipelineStepInput:
    """Build one approval gate input."""

    return PipelineStepInput(
        type="human_gate",
        gate_type="approval",
    )


def quiz_step(
    *,
    minimum: int = 5,
    questions: int = 10,
    options: int = 3,
) -> PipelineStepInput:
    """Build one configured quiz gate input."""

    return PipelineStepInput(
        type="human_gate",
        gate_type="quiz",
        config=PipelineQuizConfigInput(
            minimum_correct_answers=minimum,
            question_count=questions,
            option_count=options,
        ),
    )


def payload(
    *,
    steps: tuple[PipelineStepInput, ...] | None = None,
    title: str = "Implementation",
) -> PipelineCreate:
    """Build one valid create input."""

    return PipelineCreate(
        title=title,
        description="Implement and validate.",
        steps=(
            steps
            if steps is not None
            else (loop_step(), approval_step())
        ),
    )


def build_service(
    *,
    tenant_service: TenantService,
    repository: FakePipelineRepository | None = None,
    loop_repository: FakeLoopRepository | None = None,
) -> tuple[PipelineService, FakePipelineRepository, FakeLoopRepository]:
    """Build deterministic pipeline dependencies with one active loop."""

    pipeline_repository = repository or FakePipelineRepository()
    loops = loop_repository or FakeLoopRepository()
    loop = build_loop()
    loops.documents.setdefault((loop.workspace_id, loop.id), loop)
    identifiers = count(1)
    return (
        PipelineService(
            repository=pipeline_repository,
            loop_repository=loops,
            tenant_service=tenant_service,
            id_factory=lambda: f"id-{next(identifiers)}",
            clock=IncrementingClock(),
        ),
        pipeline_repository,
        loops,
    )


@pytest.mark.asyncio
async def test_create_preserves_order_duplicates_and_quiz_defaults(
    tenant_service: TenantService,
) -> None:
    """Creation retains repeated steps and default quiz limits."""

    service, repository, _ = build_service(
        tenant_service=tenant_service,
    )
    created = await service.create(
        user_id="user-1",
        payload=payload(
            steps=(
                loop_step(),
                loop_step(),
                quiz_step(),
                approval_step(),
                approval_step(),
            )
        ),
    )

    assert created.enabled is True
    assert [step.type for step in created.steps] == [
        "loop",
        "loop",
        "human_gate",
        "human_gate",
        "human_gate",
    ]
    quiz = created.steps[2]
    assert isinstance(quiz, PipelineHumanGateStep)
    assert quiz.config is not None
    assert quiz.config.question_count == 10
    assert quiz.config.option_count == 3
    assert quiz.config.minimum_correct_answers == 5
    assert repository.entries[-1].change_type == "created"


@pytest.mark.asyncio
@pytest.mark.parametrize("steps", [(), (loop_step(),)])
async def test_create_rejects_fewer_than_two_steps(
    tenant_service: TenantService,
    steps: tuple[PipelineStepInput, ...],
) -> None:
    """Complete validation rejects empty and single-step pipelines."""

    service, _, _ = build_service(tenant_service=tenant_service)

    with pytest.raises(InvalidPipelineStepsError):
        await service.create(
            user_id="user-1",
            payload=payload(steps=steps),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "step",
    [
        quiz_step(minimum=0),
        quiz_step(minimum=-1),
        quiz_step(questions=0),
        quiz_step(questions=-1),
        quiz_step(options=1),
        quiz_step(options=0),
        quiz_step(minimum=11, questions=10),
        PipelineStepInput(type="human_gate", gate_type="quiz"),
        PipelineStepInput(
            type="human_gate",
            gate_type="approval",
            config=PipelineQuizConfigInput(
                minimum_correct_answers=1,
            ),
        ),
    ],
)
async def test_create_rejects_invalid_quiz_configuration(
    tenant_service: TenantService,
    step: PipelineStepInput,
) -> None:
    """Quiz thresholds and gate-specific configuration are enforced."""

    service, _, _ = build_service(tenant_service=tenant_service)

    with pytest.raises(InvalidPipelineStepsError):
        await service.create(
            user_id="user-1",
            payload=payload(steps=(loop_step(), step)),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["disabled", "archived"])
async def test_create_rejects_non_active_loop_references(
    tenant_service: TenantService,
    status: str,
) -> None:
    """Disabled, archived, and missing loops use loop_not_found semantics."""

    loops = FakeLoopRepository()
    loop = build_loop(status=status)
    loops.documents[(loop.workspace_id, loop.id)] = loop
    service, _, _ = build_service(
        tenant_service=tenant_service,
        loop_repository=loops,
    )

    with pytest.raises(LoopNotFoundError):
        await service.create(user_id="user-1", payload=payload())


@pytest.mark.asyncio
async def test_patch_replaces_steps_and_records_position_diff(
    tenant_service: TenantService,
) -> None:
    """PATCH replaces the full array and records changes and movements."""

    service, repository, _ = build_service(
        tenant_service=tenant_service,
    )
    created = await service.create(
        user_id="user-1",
        payload=payload(steps=(loop_step(), approval_step())),
    )
    updated = await service.patch(
        user_id="user-1",
        pipeline_id=created.id,
        payload=PipelinePatch(
            provided_fields=frozenset({"steps"}),
            steps=(approval_step(), loop_step(), quiz_step(minimum=8)),
        ),
    )

    assert [step.type for step in updated.steps] == [
        "human_gate",
        "loop",
        "human_gate",
    ]
    step_diff = repository.entries[-1].diff["steps"]
    assert step_diff["changed"]
    assert step_diff["added"][0]["position"] == 2
    assert step_diff["order_changes"]


@pytest.mark.asyncio
async def test_enable_disable_archive_and_filtered_listing(
    tenant_service: TenantService,
) -> None:
    """Enablement, archival, filtering, search, and immutability compose."""

    service, repository, _ = build_service(
        tenant_service=tenant_service,
    )
    created = await service.create(
        user_id="user-1",
        payload=payload(title="Knowledge validation"),
    )
    disabled = await service.patch(
        user_id="user-1",
        pipeline_id=created.id,
        payload=PipelinePatch(
            provided_fields=frozenset({"enabled"}),
            enabled=False,
        ),
    )
    assert disabled.enabled is False
    assert repository.entries[-1].change_type == "disabled"

    await service.archive(user_id="user-1", pipeline_id=created.id)
    default_items, default_total = await service.list(
        user_id="user-1",
        offset=0,
    )
    archived_items, archived_total = await service.list(
        user_id="user-1",
        offset=0,
        status="archived",
        search="KNOWLEDGE",
    )

    assert default_items == []
    assert default_total == 0
    assert archived_total == 1
    assert archived_items[0].status == "archived"
    with pytest.raises(PipelineArchivedError):
        await service.patch(
            user_id="user-1",
            pipeline_id=created.id,
            payload=PipelinePatch(
                provided_fields=frozenset({"enabled"}),
                enabled=True,
            ),
        )
