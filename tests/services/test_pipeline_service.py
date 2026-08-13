"""Unit tests for pipeline application behavior."""

from __future__ import annotations

from itertools import count

import pytest

from src.app.services.pipelines.service import PipelineService
from src.app.services.pipelines.types import (
    InvalidPipelineStepsError,
    PipelineActivityDependencyInput,
    PipelineArchivedError,
    PipelineActivityInput,
    PipelineCreate,
    PipelinePatch,
)
from src.app.services.shared.tenant import TenantService
from tests.conftest import IncrementingClock
from tests.fakes.pipeline_repository import FakePipelineRepository


def activity_step(
    name: str = 'Implementation activity',
    depends_on: tuple[PipelineActivityDependencyInput, ...] = (),
) -> PipelineActivityInput:
    """Build one inline direct-loop Activity input."""

    return PipelineActivityInput(
        name=name,
        description='Complete one stage.',
        type='direct_loop',
        config={
            'stop_conditions': {'max_iterations': 1},
            'agents': [],
            'output_contract': {
                'type': 'text',
                'description': 'A pipeline stage result.',
            },
        },
        depends_on=depends_on,
    )


def dependency(activity: str, condition: str = 'success') -> PipelineActivityDependencyInput:
    """Build one named pipeline dependency condition."""

    return PipelineActivityDependencyInput(
        activity=activity,
        condition=condition,  # type: ignore[arg-type]
    )


def payload(
    *,
    steps: tuple[PipelineActivityInput, ...] | None = None,
    name: str = 'Implementation',
) -> PipelineCreate:
    """Build one valid create input."""

    return PipelineCreate(
        name=name,
        description='Implement and validate.',
        steps=(
            steps
            if steps is not None
            else (activity_step(), activity_step('Validation activity'))
        ),
    )


def build_service(
    *,
    tenant_service: TenantService,
    repository: FakePipelineRepository | None = None,
) -> tuple[PipelineService, FakePipelineRepository]:
    """Build deterministic Pipeline service dependencies."""

    pipeline_repository = repository or FakePipelineRepository()
    identifiers = count(1)
    return (
        PipelineService(
            repository=pipeline_repository,
            tenant_service=tenant_service,
            id_factory=lambda: f'id-{next(identifiers)}',
            clock=IncrementingClock(),
        ),
        pipeline_repository,
    )


@pytest.mark.asyncio
async def test_create_preserves_order_and_duplicates(
    tenant_service: TenantService,
) -> None:
    """Creation retains repeated activity references in their input order."""

    service, repository = build_service(tenant_service=tenant_service)
    created = await service.create(
        user_id='user-1',
        payload=payload(
            steps=(
                activity_step('activity-2'),
                activity_step(),
                activity_step('activity-2'),
            )
        ),
    )

    assert len(created.steps) == 3
    assert len({step.activity_id for step in created.steps}) == 3
    assert len(repository.activity_documents) == 3
    assert repository.entries[-1].change_type == 'created'


@pytest.mark.asyncio
@pytest.mark.parametrize('steps', [(), (activity_step(),)])
async def test_create_rejects_fewer_than_two_steps(
    tenant_service: TenantService,
    steps: tuple[PipelineActivityInput, ...],
) -> None:
    """Complete validation rejects empty and single-step pipelines."""

    service, _ = build_service(tenant_service=tenant_service)

    with pytest.raises(InvalidPipelineStepsError):
        await service.create(user_id='user-1', payload=payload(steps=steps))


@pytest.mark.asyncio
async def test_create_resolves_named_dependency_graph(
    tenant_service: TenantService,
) -> None:
    """Named dependencies resolve to generated Activities and retain conditions."""

    service, _ = build_service(tenant_service=tenant_service)
    created = await service.create(
        user_id='user-1',
        payload=payload(
            steps=(
                activity_step('Prepare'),
                activity_step(
                    'Validate',
                    depends_on=(dependency('Prepare'),),
                ),
                activity_step(
                    'Notify',
                    depends_on=(
                        dependency('Validate'),
                        dependency('Prepare', 'failure'),
                    ),
                ),
            ),
        ),
    )

    assert created.steps[0].depends_on == ()
    assert created.steps[1].depends_on[0].activity_id == created.steps[0].activity_id
    assert created.steps[1].depends_on[0].condition == 'success'
    assert [item.condition for item in created.steps[2].depends_on] == [
        'success',
        'failure',
    ]
    assert [item.activity_id for item in created.steps[2].depends_on] == [
        created.steps[1].activity_id,
        created.steps[0].activity_id,
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'steps',
    [
        (
            activity_step(
                'First',
                depends_on=(dependency('Missing'),),
            ),
            activity_step('Second'),
        ),
        (
            activity_step(
                'First',
                depends_on=(dependency('First'),),
            ),
            activity_step('Second'),
        ),
        (
            activity_step('Duplicate'),
            activity_step(
                'Duplicate',
                depends_on=(dependency('Duplicate'),),
            ),
        ),
        (
            activity_step(
                'First',
                depends_on=(dependency('Second'), dependency('Second', 'failure')),
            ),
            activity_step(
                'Second',
                depends_on=(dependency('First'),),
            ),
        ),
    ],
)
async def test_create_rejects_invalid_dependency_graph(
    tenant_service: TenantService,
    steps: tuple[PipelineActivityInput, ...],
) -> None:
    """Pipeline dependencies must name valid, unambiguous, acyclic edges."""

    service, _ = build_service(tenant_service=tenant_service)

    with pytest.raises(InvalidPipelineStepsError):
        await service.create(user_id='user-1', payload=payload(steps=steps))


@pytest.mark.asyncio
async def test_patch_creates_replacement_activity_records(
    tenant_service: TenantService,
) -> None:
    """Replacing steps retains prior Activities and creates new records."""

    service, repository = build_service(tenant_service=tenant_service)
    created = await service.create(user_id='user-1', payload=payload())
    updated = await service.patch(
        user_id='user-1',
        pipeline_id=created.id,
        payload=PipelinePatch(
            provided_fields=frozenset({'steps'}),
            steps=(activity_step('Review activity'), activity_step('Approval activity')),
        ),
    )

    assert len(repository.activity_documents) == 4
    assert {step.activity_id for step in created.steps}.isdisjoint(
        {step.activity_id for step in updated.steps}
    )


@pytest.mark.asyncio
async def test_patch_replaces_steps_and_records_position_diff(
    tenant_service: TenantService,
) -> None:
    """PATCH replaces the full reference array and records movements."""

    service, repository = build_service(tenant_service=tenant_service)
    created = await service.create(user_id='user-1', payload=payload())
    updated = await service.patch(
        user_id='user-1',
        pipeline_id=created.id,
        payload=PipelinePatch(
            provided_fields=frozenset({'steps'}),
            steps=(activity_step('Review activity'), activity_step('Approval activity')),
        ),
    )

    assert len(updated.steps) == 2
    assert repository.entries[-1].diff['steps']['changed']
    assert repository.entries[-1].diff['steps']['changed']


@pytest.mark.asyncio
async def test_enable_disable_archive_and_filtered_listing(
    tenant_service: TenantService,
) -> None:
    """Enablement, archival, filtering, search, and immutability compose."""

    service, repository = build_service(tenant_service=tenant_service)
    created = await service.create(
        user_id='user-1',
        payload=payload(name='Knowledge validation'),
    )
    disabled = await service.patch(
        user_id='user-1',
        pipeline_id=created.id,
        payload=PipelinePatch(
            provided_fields=frozenset({'enabled'}),
            enabled=False,
        ),
    )
    assert disabled.enabled is False
    assert repository.entries[-1].change_type == 'disabled'

    await service.archive(user_id='user-1', pipeline_id=created.id)
    default_items, default_total = await service.list(user_id='user-1', offset=0)
    archived_items, archived_total = await service.list(
        user_id='user-1',
        offset=0,
        status='archived',
        search='KNOWLEDGE',
    )

    assert default_items == []
    assert default_total == 0
    assert archived_total == 1
    assert archived_items[0].status == 'archived'
    with pytest.raises(PipelineArchivedError):
        await service.patch(
            user_id='user-1',
            pipeline_id=created.id,
            payload=PipelinePatch(
                provided_fields=frozenset({'enabled'}),
                enabled=True,
            ),
        )
