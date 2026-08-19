"""Application service for dependency-aware pipeline execution."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from secrets import token_urlsafe
from typing import Callable, Mapping

from src.app.models.activity import ActivityDocument
from src.app.models.activity_run import ActivityRunDocument
from src.app.models.pipeline import PipelineDetails
from src.app.models.pipeline_run import PipelineRunDocument, PipelineRunStepDocument
from src.app.repositories.activity_runs.repository import ActivityRunRepository
from src.app.repositories.pipeline_runs.repository import PipelineRunRepository
from src.app.services.pipelines.service import PipelineService
from src.app.services.pipeline_runs.types import (
    PipelineRunNotFoundError,
    PipelineRunUnavailableError,
)
from src.app.services.shared.tenant import TenantService


class PipelineRunService:
    """Schedule pipeline steps through persisted activity-run checkpoints."""

    def __init__(
        self,
        *,
        repository: PipelineRunRepository,
        activity_run_repository: ActivityRunRepository,
        pipeline_service: PipelineService,
        tenant_service: TenantService,
        id_factory: Callable[[], str],
        clock: Callable[[], datetime],
        token_factory: Callable[[], str] = lambda: token_urlsafe(32),
    ) -> None:
        """Store persistence, pipeline access, tenancy, and generated values."""

        self._repository = repository
        self._activity_run_repository = activity_run_repository
        self._pipeline_service = pipeline_service
        self._tenant_service = tenant_service
        self._id_factory = id_factory
        self._clock = clock
        self._token_factory = token_factory

    async def create(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        input_text: str,
        requested_workspace_id: str | None = None,
    ) -> tuple[PipelineRunDocument, ActivityRunDocument | None]:
        """Create a frozen pipeline run for a runtime worker to claim."""

        details = await self._pipeline_service.describe(
            user_id=user_id,
            pipeline_id=pipeline_id,
            requested_workspace_id=requested_workspace_id,
        )
        if details.document.status != 'active':
            raise PipelineRunUnavailableError(
                pipeline_id=pipeline_id,
                reason=f'status is {details.document.status}',
            )
        now = self._clock()
        document = PipelineRunDocument(
            id=self._id_factory(), workspace_id=details.document.workspace_id,
            pipeline_id=details.document.id, input=self._require_text(input_text),
            status='queued', worker_id=None, lease_token=None,
            lease_expires_at=None, attempt=0, current_activity_run_id=None,
            pipeline_snapshot=self._pipeline_snapshot(details),
            steps=tuple(
                PipelineRunStepDocument(
                    position=position, activity_id=activity.id, status='pending',
                    activity_run_id=None, activity_snapshot=self._activity_snapshot(activity),
                    updated_at=now,
                )
                for position, activity in enumerate(details.activities)
            ),
            created_at=now, created_by=self._require_text(user_id), updated_at=now,
        )
        return await self._repository.create(document=document, activity_run=None), None

    async def claim_next(
        self,
        *,
        user_id: str,
        worker_id: str,
        lease_duration: timedelta,
        requested_workspace_id: str | None = None,
    ) -> tuple[PipelineRunDocument, ActivityRunDocument, str] | None:
        """Atomically assign one queued or expired run to a runtime worker."""

        normalized_worker_id = self._require_text(worker_id)
        workspace = await self._tenant_service.resolve(
            user_id=user_id, requested_workspace_id=requested_workspace_id,
        )
        now = self._clock()
        candidate = await self._repository.find_claimable(
            workspace_id=workspace.workspace_id, claimed_before=now,
        )
        if candidate is None:
            return None
        if candidate.current_activity_run_id is None:
            selected, child = self._schedule(document=candidate, user_id=user_id)
        else:
            selected = candidate
            child = await self._current_child(candidate)
        if child is None:
            return None
        lease_token = self._token_factory()
        claimed = replace(
            selected, status='claimed', worker_id=normalized_worker_id,
            lease_token=lease_token, lease_expires_at=now + lease_duration,
            attempt=candidate.attempt + 1, updated_at=now,
        )
        if not await self._repository.claim(
            document=claimed, expected_updated_at=candidate.updated_at,
            expected_current_activity_run_id=candidate.current_activity_run_id,
            activity_run=(
                child
                if candidate.current_activity_run_id is None
                else None
            ),
        ):
            return None
        return claimed, child, lease_token

    async def get(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        run_id: str,
        requested_workspace_id: str | None = None,
    ) -> tuple[PipelineRunDocument, ActivityRunDocument | None]:
        """Return a pipeline run with its currently selected child, if any."""

        workspace = await self._tenant_service.resolve(
            user_id=user_id, requested_workspace_id=requested_workspace_id,
        )
        document = await self._repository.get(
            workspace_id=workspace.workspace_id, pipeline_id=pipeline_id, run_id=run_id,
        )
        if document is None:
            raise PipelineRunNotFoundError(pipeline_id=pipeline_id, run_id=run_id)
        return document, await self._current_child(document)

    async def renew_lease(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        run_id: str,
        lease_token: str,
        lease_duration: timedelta,
        requested_workspace_id: str | None = None,
    ) -> PipelineRunDocument:
        """Extend an active Pipeline worker lease by the configured duration."""

        document, _ = await self.get(
            user_id=user_id, pipeline_id=pipeline_id, run_id=run_id,
            requested_workspace_id=requested_workspace_id,
        )
        now = self._clock()
        token = self._require_text(lease_token)
        renewed = replace(
            document,
            lease_expires_at=now + lease_duration,
            updated_at=now,
        )
        if not await self._repository.renew_lease(
            document=renewed,
            expected_lease_token=token,
            now=now,
        ):
            raise PipelineRunUnavailableError(
                pipeline_id=pipeline_id,
                reason='lease is no longer active',
            )
        return renewed

    async def continue_run(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        run_id: str,
        lease_token: str,
        requested_workspace_id: str | None = None,
    ) -> tuple[PipelineRunDocument, ActivityRunDocument | None]:
        """Record the current child outcome and schedule the next eligible step."""

        document, child = await self.get(
            user_id=user_id, pipeline_id=pipeline_id, run_id=run_id,
            requested_workspace_id=requested_workspace_id,
        )
        now = self._clock()
        token = self._require_text(lease_token)
        if (
            document.lease_token != token
            or document.lease_expires_at is None
            or document.lease_expires_at <= now
        ):
            raise PipelineRunUnavailableError(
                pipeline_id=pipeline_id,
                reason='lease is no longer active',
            )
        if document.status not in ('claimed', 'in_progress') or child is None:
            return document, child
        if child.status == 'in_progress':
            return document, child
        updated = self._record_child_outcome(document=document, child=child)
        selected, next_child = self._schedule(document=updated, user_id=user_id)
        if await self._repository.transition(
            document=selected,
            expected_current_activity_run_id=child.id,
            expected_lease_token=token,
            now=now,
            activity_run=next_child,
        ):
            return selected, next_child
        return await self.get(
            user_id=user_id, pipeline_id=pipeline_id, run_id=run_id,
            requested_workspace_id=requested_workspace_id,
        )

    async def _current_child(
        self,
        document: PipelineRunDocument,
    ) -> ActivityRunDocument | None:
        """Return the current child run using its frozen owning activity ID."""

        if document.current_activity_run_id is None:
            return None
        step = next(
            value for value in document.steps
            if value.activity_run_id == document.current_activity_run_id
        )
        return await self._activity_run_repository.get(
            workspace_id=document.workspace_id,
            activity_id=step.activity_id,
            run_id=document.current_activity_run_id,
        )

    def _schedule(
        self,
        *,
        document: PipelineRunDocument,
        user_id: str,
    ) -> tuple[PipelineRunDocument, ActivityRunDocument | None]:
        """Skip impossible branches and issue the first dependency-ready step."""

        now = self._clock()
        steps = list(document.steps)
        by_activity_id = {step.activity_id: step for step in steps}
        dependencies = self._dependencies(document.pipeline_snapshot)
        for index, step in enumerate(steps):
            if step.status != 'pending':
                continue
            requirements = dependencies[step.activity_id]
            if all(by_activity_id[item['activity_id']].status in ('completed', 'failed', 'skipped') for item in requirements) and any(
                by_activity_id[item['activity_id']].status != item['condition']
                for item in requirements
            ):
                steps[index] = replace(step, status='skipped', updated_at=now)
        by_activity_id = {step.activity_id: step for step in steps}
        ready = next(
            (
                step for step in steps
                if step.status == 'pending'
                and all(
                    by_activity_id[item['activity_id']].status == item['condition']
                    for item in dependencies[step.activity_id]
                )
            ),
            None,
        )
        if ready is None:
            status = 'completed' if all(
                step.status in ('completed', 'failed', 'skipped') for step in steps
            ) else 'in_progress'
            return replace(document, status=status, steps=tuple(steps), updated_at=now), None
        child = ActivityRunDocument(
            id=self._id_factory(), workspace_id=document.workspace_id,
            activity_id=ready.activity_id, input=document.input,
            status='in_progress', state='awaiting_snapshot',
            next_action='collect_snapshot', iteration=1, token_revision=0,
            continuation_token=self._token_factory(), activity_snapshot=ready.activity_snapshot,
            execution_context={}, created_at=now, created_by=user_id, updated_at=now,
        )
        selected_steps = tuple(
            replace(step, status='in_progress', activity_run_id=child.id, updated_at=now)
            if step.position == ready.position else step
            for step in steps
        )
        return replace(
            document, current_activity_run_id=child.id, steps=selected_steps,
            updated_at=now,
        ), child

    def _record_child_outcome(
        self,
        *,
        document: PipelineRunDocument,
        child: ActivityRunDocument,
    ) -> PipelineRunDocument:
        """Persist the current child terminal result before scheduling successors."""

        if child.status not in ('completed', 'failed', 'stopped'):
            raise PipelineRunUnavailableError(
                pipeline_id=document.pipeline_id,
                reason='current activity run is not terminal',
            )
        status = 'completed' if child.status == 'completed' else 'failed'
        now = self._clock()
        return replace(
            document, current_activity_run_id=None, updated_at=now,
            steps=tuple(
                replace(step, status=status, updated_at=now)
                if step.activity_run_id == child.id else step
                for step in document.steps
            ),
        )

    @staticmethod
    def _pipeline_snapshot(details: PipelineDetails) -> dict[str, object]:
        """Capture graph dependencies by immutable activity IDs for scheduling."""

        return {
            'pipeline_id': details.document.id,
            'steps': [
                {
                    'activity_id': step.activity_id,
                    'depends_on': [
                        {'activity_id': dependency.activity_id, 'condition': dependency.condition}
                        for dependency in step.depends_on
                    ],
                }
                for step in details.document.steps
            ],
        }

    @staticmethod
    def _activity_snapshot(activity: ActivityDocument) -> dict[str, object]:
        """Freeze an executable activity in the format used by activity runs."""

        flows = {'direct_loop': 'direct', 'roundtable_loop': 'roundtable'}
        flow = flows.get(activity.type)
        if flow is None:
            raise PipelineRunUnavailableError(
                pipeline_id='unknown', reason=f'activity {activity.id} is not executable',
            )
        return {
            'id': activity.id, 'title': activity.name,
            'description': activity.description, **activity.config, 'flow': flow,
        }

    @staticmethod
    def _dependencies(snapshot: Mapping[str, object]) -> dict[str, list[dict[str, str]]]:
        """Return validated dependency requirements by activity ID."""

        values = snapshot.get('steps')
        if not isinstance(values, list):
            raise RuntimeError('Pipeline run snapshot is invalid.')
        return {
            str(step['activity_id']): [
                {
                    'activity_id': str(item['activity_id']),
                    'condition': (
                        'completed'
                        if item['condition'] == 'success'
                        else 'failed'
                    ),
                }
                for item in step['depends_on']
            ]
            for step in values
            if isinstance(step, dict)
        }

    @staticmethod
    def _require_text(value: str) -> str:
        """Require non-empty user input and actor IDs."""

        normalized = value.strip()
        if not normalized:
            raise ValueError('Pipeline run input must not be empty.')
        return normalized
