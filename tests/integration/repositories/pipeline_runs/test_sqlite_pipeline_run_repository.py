"""Integration tests for SQLite pipeline-run claim persistence."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.app.models.activity import ActivityChangelogEntry, ActivityDocument
from src.app.models.activity_run import ActivityRunDocument
from src.app.models.pipeline import PipelineActivityStep, PipelineDocument
from src.app.models.pipeline_run import PipelineRunDocument, PipelineRunStepDocument
from src.app.repositories.pipelines.sqlite_repository import SqlitePipelineRepository
from src.app.repositories.pipeline_runs.sqlite_repository import SqlitePipelineRunRepository


@pytest.mark.asyncio
async def test_claim_inserts_initial_child_before_referencing_it(
    sqlite_database_path: Path,
    create_workspace: object,
) -> None:
    """A started run claim atomically creates and selects its first Activity child."""

    timestamp = datetime(2026, 8, 19, tzinfo=UTC)
    await create_workspace(
        project_id='workspace-1',
        memberships=(('user-1', 'owner', True),),
    )
    activity = ActivityDocument(
        id='activity-1', name='Activity',
        description='Complete one stage.', status='active', type='direct_loop',
        config={'type': 'direct_loop'}, created_at=timestamp, created_by='user-1',
        updated_at=timestamp, updated_by='user-1',
    )
    pipeline = PipelineDocument(
        id='pipeline-1', name='Pipeline',
        description='Run one stage.', status='active',
        steps=(PipelineActivityStep(activity_id=activity.id),),
        created_at=timestamp, created_by='user-1', updated_at=timestamp,
        updated_by='user-1',
    )
    await SqlitePipelineRepository(sqlite_database_path).create_with_activities(
        document=pipeline,
        changelog_entry=_pipeline_entry(pipeline, timestamp),
        activity_documents=[activity],
        activity_changelog_entries=[_activity_entry(activity, timestamp)],
    )
    repository = SqlitePipelineRunRepository(sqlite_database_path)
    prepared = PipelineRunDocument(
        id='run-1', project_id='workspace-1', pipeline_id=pipeline.id,
        input='Implement.', status='prepared', worker_id=None, lease_token=None,
        lease_expires_at=None, attempt=0, current_activity_run_id=None,
        pipeline_snapshot={'steps': []},
        steps=(
            PipelineRunStepDocument(
                position=0, activity_id=activity.id, status='pending',
                activity_run_id=None, activity_snapshot={'flow': 'direct'},
                updated_at=timestamp,
            ),
        ),
        created_at=timestamp, created_by='user-1', updated_at=timestamp,
        commit_mode='forbid',
    )
    await repository.create(document=prepared, activity_run=None)
    listed, total = await repository.list(
        project_id='workspace-1',
        offset=0,
        limit=10,
        pipeline_id=pipeline.id,
        status='prepared',
        created_from=timestamp - timedelta(seconds=1),
        created_to=timestamp + timedelta(seconds=1),
    )
    excluded, excluded_total = await repository.list(
        project_id='workspace-1',
        offset=0,
        limit=10,
        pipeline_id=None,
        status='completed',
        created_from=None,
        created_to=None,
    )

    assert listed == [prepared]
    assert total == 1
    assert excluded == []
    assert excluded_total == 0

    queued = replace(
        prepared,
        status='queued',
        updated_at=timestamp + timedelta(seconds=1),
    )
    started = await repository.start(
        document=queued,
        expected_updated_at=prepared.updated_at,
        activity_run=None,
    )
    assert started is True
    child = ActivityRunDocument(
        id='activity-run-1', project_id='workspace-1', activity_id=activity.id,
        input='Implement.', status='in_progress', state='awaiting_snapshot',
        next_action='collect_snapshot', iteration=1, token_revision=0,
        continuation_token='token-1', activity_snapshot={'flow': 'direct'},
        execution_context={}, created_at=timestamp, created_by='user-1',
        updated_at=timestamp,
    )
    claimed = replace(
        queued, status='claimed', worker_id='worker-1', lease_token='lease-1',
        lease_expires_at=timestamp + timedelta(minutes=1), attempt=1,
        current_activity_run_id=child.id,
        steps=(replace(queued.steps[0], status='in_progress', activity_run_id=child.id),),
    )

    persisted = await repository.claim(
        document=claimed,
        expected_updated_at=queued.updated_at,
        expected_current_activity_run_id=queued.current_activity_run_id,
        activity_run=child,
    )
    fetched = await repository.get(
        project_id='workspace-1', pipeline_id=pipeline.id, run_id=queued.id,
    )

    assert persisted is True
    assert fetched == claimed

    successor = replace(
        child,
        id='activity-run-2',
        continuation_token='token-2',
    )
    advanced = replace(
        claimed,
        current_activity_run_id=successor.id,
        steps=(
            replace(
                claimed.steps[0],
                activity_run_id=successor.id,
                updated_at=timestamp + timedelta(seconds=1),
            ),
        ),
        updated_at=timestamp + timedelta(seconds=1),
    )

    transitioned = await repository.transition(
        document=advanced,
        expected_current_activity_run_id=child.id,
        expected_lease_token='lease-1',
        now=timestamp,
        activity_run=successor,
    )
    fetched_successor = await repository.get(
        project_id='workspace-1', pipeline_id=pipeline.id, run_id=queued.id,
    )

    assert transitioned is True
    assert fetched_successor == advanced


def _pipeline_entry(pipeline: PipelineDocument, timestamp: datetime) -> object:
    """Build the changelog entry required by Pipeline persistence."""

    from src.app.models.pipeline import PipelineChangelogEntry

    return PipelineChangelogEntry(
        id='pipeline-entry-1', pipeline_id=pipeline.id,
        change_type='created', actor_id='user-1', changed_at=timestamp, diff=None,
        content={'id': pipeline.id},
    )


def _activity_entry(activity: ActivityDocument, timestamp: datetime) -> ActivityChangelogEntry:
    """Build the changelog entry required by generated Activity persistence."""

    return ActivityChangelogEntry(
        id='activity-entry-1', activity_id=activity.id,
        change_type='created', actor_id='user-1', changed_at=timestamp, diff=None,
        content={'id': activity.id},
    )
