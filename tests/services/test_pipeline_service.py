"""Unit tests for pipeline application behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import count

import pytest

from src.app.models.activity import ActivityDocument
from src.app.services.pipelines.service import PipelineService
from src.app.services.pipelines.types import (
    InvalidPipelineStepsError,
    PipelineArchivedError,
    PipelineCreate,
    PipelinePatch,
    PipelineStepInput,
)
from src.app.services.shared.reference_resolver import ResourceNotFoundError
from src.app.services.shared.tenant import TenantService
from tests.conftest import IncrementingClock
from tests.fakes.activity_repository import FakeActivityRepository
from tests.fakes.pipeline_repository import FakePipelineRepository


def activity_step(activity_id: str = 'activity-1') -> PipelineStepInput:
    """Build one activity-reference input."""

    return PipelineStepInput(activity_id=activity_id)


def build_activity(
    *,
    activity_id: str,
    status: str = 'active',
) -> ActivityDocument:
    """Build one workspace activity suitable for a pipeline reference."""

    timestamp = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)
    return ActivityDocument(
        id=activity_id,
        workspace_id='workspace-1',
        title=f'Activity {activity_id}',
        description='Complete one stage.',
        status=status,  # type: ignore[arg-type]
        type='loop',
        config={'type': 'loop'},
        created_at=timestamp,
        created_by='user-1',
        updated_at=timestamp,
        updated_by='user-1',
    )


def payload(
    *,
    steps: tuple[PipelineStepInput, ...] | None = None,
    title: str = 'Implementation',
) -> PipelineCreate:
    """Build one valid create input."""

    return PipelineCreate(
        title=title,
        description='Implement and validate.',
        steps=(
            steps
            if steps is not None
            else (activity_step(), activity_step('activity-2'))
        ),
    )


def build_service(
    *,
    tenant_service: TenantService,
    repository: FakePipelineRepository | None = None,
    activity_repository: FakeActivityRepository | None = None,
) -> tuple[PipelineService, FakePipelineRepository, FakeActivityRepository]:
    """Build deterministic pipeline dependencies with active activities."""

    pipeline_repository = repository or FakePipelineRepository()
    activities = activity_repository or FakeActivityRepository()
    for activity_id in ('activity-1', 'activity-2', 'activity-3'):
        activity = build_activity(activity_id=activity_id)
        activities.documents.setdefault(
            (activity.workspace_id, activity.id),
            activity,
        )
    identifiers = count(1)
    return (
        PipelineService(
            repository=pipeline_repository,
            activity_repository=activities,
            tenant_service=tenant_service,
            id_factory=lambda: f'id-{next(identifiers)}',
            clock=IncrementingClock(),
        ),
        pipeline_repository,
        activities,
    )


@pytest.mark.asyncio
async def test_create_preserves_order_and_duplicates(
    tenant_service: TenantService,
) -> None:
    """Creation retains repeated activity references in their input order."""

    service, repository, _ = build_service(tenant_service=tenant_service)
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

    assert [step.activity_id for step in created.steps] == [
        'activity-2',
        'activity-1',
        'activity-2',
    ]
    assert repository.entries[-1].change_type == 'created'


@pytest.mark.asyncio
@pytest.mark.parametrize('steps', [(), (activity_step(),)])
async def test_create_rejects_fewer_than_two_steps(
    tenant_service: TenantService,
    steps: tuple[PipelineStepInput, ...],
) -> None:
    """Complete validation rejects empty and single-step pipelines."""

    service, _, _ = build_service(tenant_service=tenant_service)

    with pytest.raises(InvalidPipelineStepsError):
        await service.create(user_id='user-1', payload=payload(steps=steps))


@pytest.mark.asyncio
@pytest.mark.parametrize('status', ['disabled', 'archived'])
async def test_create_rejects_non_active_activity_references(
    tenant_service: TenantService,
    status: str,
) -> None:
    """Inactive and missing activities use referenced-resource semantics."""

    activities = FakeActivityRepository()
    inactive = build_activity(activity_id='activity-1', status=status)
    active = build_activity(activity_id='activity-2')
    activities.documents[(inactive.workspace_id, inactive.id)] = inactive
    activities.documents[(active.workspace_id, active.id)] = active
    service, _, _ = build_service(
        tenant_service=tenant_service,
        activity_repository=activities,
    )

    with pytest.raises(ResourceNotFoundError) as error:
        await service.create(user_id='user-1', payload=payload())

    assert error.value.references[0].resource_id == 'activity-1'


@pytest.mark.asyncio
async def test_patch_revalidates_existing_activity_references(
    tenant_service: TenantService,
) -> None:
    """A title-only patch rejects an activity disabled after creation."""

    service, _, activities = build_service(tenant_service=tenant_service)
    created = await service.create(user_id='user-1', payload=payload())
    inactive = build_activity(activity_id='activity-1', status='disabled')
    activities.documents[(inactive.workspace_id, inactive.id)] = inactive

    with pytest.raises(ResourceNotFoundError):
        await service.patch(
            user_id='user-1',
            pipeline_id=created.id,
            payload=PipelinePatch(
                provided_fields=frozenset({'title'}),
                title='Renamed pipeline',
            ),
        )


@pytest.mark.asyncio
async def test_patch_replaces_steps_and_records_position_diff(
    tenant_service: TenantService,
) -> None:
    """PATCH replaces the full reference array and records movements."""

    service, repository, _ = build_service(tenant_service=tenant_service)
    created = await service.create(user_id='user-1', payload=payload())
    updated = await service.patch(
        user_id='user-1',
        pipeline_id=created.id,
        payload=PipelinePatch(
            provided_fields=frozenset({'steps'}),
            steps=(activity_step('activity-2'), activity_step('activity-3')),
        ),
    )

    assert [step.activity_id for step in updated.steps] == [
        'activity-2',
        'activity-3',
    ]
    assert repository.entries[-1].diff['steps']['changed']


@pytest.mark.asyncio
async def test_enable_disable_archive_and_filtered_listing(
    tenant_service: TenantService,
) -> None:
    """Enablement, archival, filtering, search, and immutability compose."""

    service, repository, _ = build_service(tenant_service=tenant_service)
    created = await service.create(
        user_id='user-1',
        payload=payload(title='Knowledge validation'),
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
