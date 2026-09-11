"""Application service for dependency-aware pipeline execution."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from secrets import token_urlsafe
from typing import Callable, Mapping

from src.app.models.activity_run import ActivityRunDocument
from src.app.models.pipeline import PipelineHarness
from src.app.models.pipeline_run import (
    PipelineRunCommitMode,
    PipelineRunDocument,
    PipelineRunStepDocument,
)
from src.app.repositories.activity_runs.repository import ActivityRunRepository
from src.app.repositories.pipeline_runs.repository import PipelineRunRepository
from src.app.services.pipelines.service import PipelineService
from src.app.services.models import ModelExecutionService
from src.app.services.models.catalog import ModelCatalogService
from src.app.services.execution_instructions import ExecutionInstructionLibraryService
from src.app.services.pipeline_runs.etag import pipeline_run_etag
from src.app.services.pipeline_runs.events import PipelineRunEventBuilder
from src.app.services.pipeline_runs.graph import (
    first_dependency_ready_step,
    snapshot_dependencies,
)
from src.app.services.pipeline_runs.readiness import (
    PipelineRunReadiness,
    PipelineRunReadinessService,
    required_harness,
)
from src.app.services.pipeline_runs.snapshot import (
    PipelineRunSnapshotBuilder,
    harness_snapshot,
)
from src.app.services.pipeline_runs.types import (
    PipelineRunNotFoundError,
    PipelineRunPreconditionFailedError,
    PipelineRunUnavailableError,
)
from src.app.services.shared.tenant import TenantService
from src.app.services.shared.pagination import PAGE_SIZE, require_offset
from src.app.services.users import UserService
from src.app.services.workers import WorkerService
from src.app.services.projects.service import ProjectService


class PipelineRunService:
    """Schedule pipeline steps through persisted activity-run checkpoints."""

    def __init__(
        self,
        *,
        repository: PipelineRunRepository,
        activity_run_repository: ActivityRunRepository,
        pipeline_service: PipelineService,
        tenant_service: TenantService,
        worker_service: WorkerService | None = None,
        workspace_service: ProjectService | None = None,
        user_service: UserService | None = None,
        model_execution_service: ModelExecutionService | None = None,
        model_catalog_service: ModelCatalogService | None = None,
        instruction_library_service: ExecutionInstructionLibraryService | None = None,
        id_factory: Callable[[], str],
        clock: Callable[[], datetime],
        token_factory: Callable[[], str] = lambda: token_urlsafe(32),
    ) -> None:
        """Store persistence, pipeline access, tenancy, and generated values."""

        self._repository = repository
        self._activity_run_repository = activity_run_repository
        self._pipeline_service = pipeline_service
        self._tenant_service = tenant_service
        self._worker_service = worker_service
        self._workspace_service = workspace_service
        self._user_service = user_service
        self._snapshot_builder = PipelineRunSnapshotBuilder(
            model_execution_service=model_execution_service,
            model_catalog_service=model_catalog_service,
            instruction_library_service=instruction_library_service,
        )
        self._id_factory = id_factory
        self._event_builder = PipelineRunEventBuilder(id_factory)
        self._readiness_service = PipelineRunReadinessService(
            repository=repository,
            tenant_service=tenant_service,
            worker_service=worker_service,
            clock=clock,
        )
        self._clock = clock
        self._token_factory = token_factory

    async def list(
        self,
        *,
        user_id: str,
        offset: int,
        created_from: datetime | None = None,
        requested_project_id: str | None = None,
    ) -> tuple[list[PipelineRunDocument], int]:
        """Return one filtered page from the selected Project's run history."""

        project = await self._tenant_service.resolve(
            user_id=user_id,
            requested_project_id=requested_project_id,
        )
        documents, total = await self._repository.list(
            project_id=project.project_id,
            offset=require_offset(offset),
            limit=PAGE_SIZE,
            created_from=created_from,
        )
        return list(documents), total

    async def create(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        input_text: str,
        commit_mode: PipelineRunCommitMode = 'allow',
        requested_project_id: str | None = None,
    ) -> tuple[PipelineRunDocument, ActivityRunDocument | None]:
        """Create a frozen Pipeline run awaiting an explicit operator start."""

        workspace = await self._tenant_service.resolve(
            user_id=user_id, requested_project_id=requested_project_id,
        )
        details = await self._pipeline_service.describe(
            user_id=user_id,
            pipeline_id=pipeline_id,
        )
        if details.document.status != 'active':
            raise PipelineRunUnavailableError(
                pipeline_id=pipeline_id,
                reason=f'status is {details.document.status}',
            )
        user_default_model_id, user_default_harness = await self._user_defaults(
            user_id=user_id,
        )
        inherited_model_id = (
            details.document.model_id
            or user_default_model_id
        )
        inherited_harness = (
            details.document.harness
            or user_default_harness
            or PipelineHarness()
        )
        now = self._clock()
        run_id = self._id_factory()
        activity_snapshots = await self._snapshot_builder.activity_snapshots(
            details.activities,
            pipeline_id=details.document.id,
            project_id=workspace.project_id,
            user_id=user_id,
            inherited_model_id=inherited_model_id,
            inherited_harness=inherited_harness,
        )
        steps = []
        for position, (activity, activity_snapshot) in enumerate(
            zip(details.activities, activity_snapshots, strict=True)
        ):
            steps.append(PipelineRunStepDocument(
                position=position, activity_id=activity.id, status='pending',
                activity_run_id=None,
                activity_snapshot=activity_snapshot,
                updated_at=now,
            ))
        document = PipelineRunDocument(
            id=run_id, project_id=workspace.project_id,
            pipeline_id=details.document.id, input=self._require_text(input_text),
            commit_mode=commit_mode,
            status='prepared', worker_id=None, lease_token=None,
            lease_expires_at=None, attempt=0, current_activity_run_id=None,
            pipeline_snapshot=self._snapshot_builder.pipeline_snapshot(
                details,
                harness=inherited_harness,
            ),
            steps=tuple(steps),
            events=(
                self._event_builder.created(
                    project_id=workspace.project_id,
                    run_id=run_id,
                    actor_id=self._require_text(user_id),
                    commit_mode=commit_mode,
                    created_at=now,
                ),
            ),
            created_at=now, created_by=self._require_text(user_id), updated_at=now,
        )
        return await self._repository.create(document=document, activity_run=None), None

    async def start(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        run_id: str,
        requested_project_id: str | None = None,
    ) -> tuple[PipelineRunDocument, ActivityRunDocument | None]:
        """Make one prepared run eligible for runtime or human execution."""

        workspace = await self._tenant_service.resolve(
            user_id=user_id, requested_project_id=requested_project_id,
        )
        details = await self._pipeline_service.describe(
            user_id=user_id,
            pipeline_id=pipeline_id,
        )
        if details.document.status != 'active':
            raise PipelineRunUnavailableError(
                pipeline_id=pipeline_id,
                reason=f'status is {details.document.status}',
            )
        document = await self._get_required(
            project_id=workspace.project_id,
            pipeline_id=details.document.id,
            run_id=run_id,
        )
        if document.status != 'prepared':
            raise PipelineRunUnavailableError(
                pipeline_id=pipeline_id,
                reason=f'run {run_id} is not prepared',
            )
        selected, child = self._schedule(
            document=document,
            user_id=user_id,
            materialize_runtime=False,
        )
        if child is not None:
            selected = replace(
                selected,
                events=self._event_builder.started_child(
                    document=selected,
                    child=child,
                    actor_id=user_id,
                    created_at=selected.updated_at,
                ),
            )
        if await self._repository.start(
            document=selected,
            expected_updated_at=document.updated_at,
            activity_run=child,
        ):
            return selected, child
        return await self.get(
            user_id=user_id,
            pipeline_id=pipeline_id,
            run_id=run_id,
            requested_project_id=requested_project_id,
        )

    async def list_claimable(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        requested_project_id: str | None = None,
    ) -> list[PipelineRunDocument]:
        """List claimable runs beneath one active Pipeline."""

        workspace = await self._tenant_service.resolve(
            user_id=user_id, requested_project_id=requested_project_id,
        )
        details = await self._pipeline_service.describe(
            user_id=user_id, pipeline_id=pipeline_id,
        )
        if details.document.status != 'active':
            return []
        now = self._clock()
        return await self._repository.list_claimable(
            project_id=workspace.project_id,
            pipeline_id=details.document.id,
            claimed_before=now,
        )

    async def claim(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        run_id: str,
        worker_id: str,
        if_match: str,
        lease_duration: timedelta,
        requested_project_id: str | None = None,
    ) -> tuple[PipelineRunDocument, ActivityRunDocument, str | None]:
        """Atomically claim one current, claimable Pipeline run."""

        normalized_worker_id = self._require_text(worker_id)
        workspace = await self._tenant_service.resolve(
            user_id=user_id, requested_project_id=requested_project_id,
        )
        details = await self._pipeline_service.describe(
            user_id=user_id, pipeline_id=pipeline_id,
        )
        if details.document.status != 'active':
            raise PipelineRunUnavailableError(
                pipeline_id=pipeline_id,
                reason=f'status is {details.document.status}',
            )
        candidate = await self._get_required(
            project_id=workspace.project_id,
            pipeline_id=details.document.id,
            run_id=run_id,
        )
        now = self._clock()
        if self._worker_service is not None:
            await self._worker_service.require_capable(
                project_id=workspace.project_id,
                worker_id=normalized_worker_id,
                harness=required_harness(candidate),
            )
        if if_match != pipeline_run_etag(candidate):
            raise PipelineRunPreconditionFailedError(
                pipeline_id=pipeline_id,
                run_id=run_id,
            )
        if not self._is_claimable(candidate, now):
            raise PipelineRunUnavailableError(
                pipeline_id=pipeline_id,
                reason=f'run {run_id} is no longer claimable',
            )
        if candidate.current_activity_run_id is None:
            selected, child = self._schedule(document=candidate, user_id=user_id)
        else:
            selected = candidate
            child = await self._current_child(candidate)
        if child is None:
            raise PipelineRunUnavailableError(
                pipeline_id=pipeline_id,
                reason=f'run {run_id} has no current activity run',
            )
        if self._is_human_child(child):
            waiting = replace(
                selected,
                status='waiting',
                worker_id=None,
                lease_token=None,
                lease_expires_at=None,
                attempt=candidate.attempt,
                updated_at=now,
            )
            if not await self._repository.claim(
                document=waiting,
                expected_updated_at=candidate.updated_at,
                expected_current_activity_run_id=candidate.current_activity_run_id,
                activity_run=None,
            ):
                raise PipelineRunPreconditionFailedError(
                    pipeline_id=pipeline_id,
                    run_id=run_id,
                )
            return waiting, child, None
        lease_token = self._token_factory()
        claimed = replace(
            selected, status='claimed', worker_id=normalized_worker_id,
            lease_token=lease_token, lease_expires_at=now + lease_duration,
            attempt=candidate.attempt + 1, updated_at=now,
        )
        claimed = replace(
            claimed,
            events=self._event_builder.claimed(
                document=claimed,
                child=child,
                worker_id=normalized_worker_id,
                created_at=now,
                step_started=candidate.current_activity_run_id is None,
            ),
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
            raise PipelineRunPreconditionFailedError(
                pipeline_id=pipeline_id,
                run_id=run_id,
            )
        return claimed, child, lease_token

    async def get(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        run_id: str,
        requested_project_id: str | None = None,
    ) -> tuple[PipelineRunDocument, ActivityRunDocument | None]:
        """Return a pipeline run with its currently selected child, if any."""

        workspace = await self._tenant_service.resolve(
            user_id=user_id, requested_project_id=requested_project_id,
        )
        document = await self._repository.get(
            project_id=workspace.project_id, pipeline_id=pipeline_id, run_id=run_id,
        )
        if document is None:
            raise PipelineRunNotFoundError(pipeline_id=pipeline_id, run_id=run_id)
        events = await self._repository.list_events(
            project_id=workspace.project_id,
            pipeline_id=pipeline_id,
            run_id=run_id,
        )
        return replace(document, events=tuple(events)), await self._current_child(document)

    async def readiness(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        run_id: str,
        requested_project_id: str | None = None,
    ) -> PipelineRunReadiness:
        """Describe whether a queued run has an active compatible Worker."""

        return await self._readiness_service.get(
            user_id=user_id, pipeline_id=pipeline_id, run_id=run_id,
            requested_project_id=requested_project_id,
        )

    async def _get_required(
        self,
        *,
        project_id: str,
        pipeline_id: str,
        run_id: str,
    ) -> PipelineRunDocument:
        """Return one run under a resolved workspace and Pipeline."""

        document = await self._repository.get(
            project_id=project_id,
            pipeline_id=pipeline_id,
            run_id=run_id,
        )
        if document is None:
            raise PipelineRunNotFoundError(pipeline_id=pipeline_id, run_id=run_id)
        return document

    async def _user_defaults(
        self,
        *,
        user_id: str,
    ) -> tuple[str | None, PipelineHarness | None]:
        """Return the lowest-priority model and Harness configured by the User."""

        if self._user_service is None:
            return None, None
        settings = (await self._user_service.get(user_id=user_id)).settings
        return settings.default_model_id, settings.default_harness

    @staticmethod
    def _is_claimable(document: PipelineRunDocument, now: datetime) -> bool:
        """Return whether a queued or expired claim may be claimed now."""

        return document.status == 'queued' or (
            document.status == 'claimed'
            and document.lease_expires_at is not None
            and document.lease_expires_at <= now
        )

    async def renew_lease(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        run_id: str,
        lease_token: str | None,
        lease_duration: timedelta,
        requested_project_id: str | None = None,
    ) -> PipelineRunDocument:
        """Extend an active Pipeline worker lease by the configured duration."""

        document, _ = await self.get(
            user_id=user_id, pipeline_id=pipeline_id, run_id=run_id,
            requested_project_id=requested_project_id,
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
        lease_token: str | None,
        requested_project_id: str | None = None,
    ) -> tuple[PipelineRunDocument, ActivityRunDocument | None]:
        """Record the current child outcome and schedule the next eligible step."""

        document, child = await self.get(
            user_id=user_id, pipeline_id=pipeline_id, run_id=run_id,
            requested_project_id=requested_project_id,
        )
        document = replace(document, events=())
        now = self._clock()
        human_child = child is not None and self._is_human_child(child)
        token = lease_token.strip() if lease_token is not None else None
        if not human_child and (
            token is None
            or document.lease_token != token
            or document.lease_expires_at is None
            or document.lease_expires_at <= now
        ):
            raise PipelineRunUnavailableError(
                pipeline_id=pipeline_id,
                reason='lease is no longer active',
            )
        if document.status not in ('claimed', 'in_progress', 'waiting') or child is None:
            return document, child
        if child.status == 'in_progress':
            return document, child
        updated = self._record_child_outcome(document=document, child=child)
        if self._requires_correction(child):
            selected = self._queue_correction(
                document=updated,
                activity_id=child.activity_id,
                now=now,
            )
            next_child = None
        else:
            selected, next_child = self._schedule(document=updated, user_id=user_id)
        selected = replace(
            selected,
            events=self._event_builder.finished_child(
                document=selected,
                child=child,
                actor_id=document.worker_id or user_id,
                created_at=now,
                next_child=next_child,
            ),
        )
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
            requested_project_id=requested_project_id,
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
            project_id=document.project_id,
            activity_id=step.activity_id,
            run_id=document.current_activity_run_id,
        )

    def _schedule(
        self,
        *,
        document: PipelineRunDocument,
        user_id: str,
        materialize_runtime: bool = True,
    ) -> tuple[PipelineRunDocument, ActivityRunDocument | None]:
        """Skip impossible branches and issue the first dependency-ready step."""

        now = self._clock()
        steps = list(document.steps)
        by_activity_id = {step.activity_id: step for step in steps}
        dependencies = snapshot_dependencies(document.pipeline_snapshot)
        for index, step in enumerate(steps):
            if step.status != 'pending':
                continue
            requirements = dependencies[step.activity_id]
            if all(by_activity_id[item['activity_id']].status in ('completed', 'failed', 'skipped') for item in requirements) and any(
                by_activity_id[item['activity_id']].status != item['condition']
                for item in requirements
            ):
                steps[index] = replace(step, status='skipped', updated_at=now)
        ready = first_dependency_ready_step(steps, dependencies)
        if ready is None:
            status = 'completed' if all(
                step.status in ('completed', 'failed', 'skipped') for step in steps
            ) else 'in_progress'
            return replace(document, status=status, steps=tuple(steps), updated_at=now), None
        human_activity = ready.activity_snapshot.get('executor') == 'human'
        if not human_activity and not materialize_runtime:
            return replace(
                document,
                status='queued',
                steps=tuple(steps),
                updated_at=now,
            ), None
        child = ActivityRunDocument(
            id=self._id_factory(), project_id=document.project_id,
            activity_id=ready.activity_id, input=document.input,
            status='in_progress',
            state='awaiting_human_decision' if human_activity else 'awaiting_snapshot',
            next_action='submit_human_decision' if human_activity else 'collect_snapshot',
            iteration=1, token_revision=0,
            continuation_token=self._token_factory(),
            activity_snapshot={
                **ready.activity_snapshot,
                'commit_mode': document.commit_mode,
                'harness': harness_snapshot(ready.activity_snapshot),
            },
            execution_context={}, created_at=now, created_by=user_id, updated_at=now,
        )
        selected_steps = tuple(
            replace(step, status='in_progress', activity_run_id=child.id, updated_at=now)
            if step.position == ready.position else step
            for step in steps
        )
        return replace(
            document,
            status='waiting' if human_activity else document.status,
            worker_id=None if human_activity else document.worker_id,
            lease_token=None if human_activity else document.lease_token,
            lease_expires_at=None if human_activity else document.lease_expires_at,
            current_activity_run_id=child.id,
            steps=selected_steps,
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

    def _queue_correction(
        self,
        *,
        document: PipelineRunDocument,
        activity_id: str,
        now: datetime,
    ) -> PipelineRunDocument:
        """Reset the rejected gate's dependency path for corrective execution."""

        dependencies = snapshot_dependencies(document.pipeline_snapshot)
        correction_ids = self._ancestors(
            activity_id=activity_id,
            dependencies=dependencies,
        )
        return replace(
            document,
            status='queued',
            worker_id=None,
            lease_token=None,
            lease_expires_at=None,
            current_activity_run_id=None,
            steps=tuple(
                replace(
                    step,
                    status='pending',
                    activity_run_id=None,
                    updated_at=now,
                )
                if step.activity_id in correction_ids | {activity_id}
                else step
                for step in document.steps
            ),
            updated_at=now,
        )

    @staticmethod
    def _ancestors(
        *,
        activity_id: str,
        dependencies: Mapping[str, list[dict[str, str]]],
    ) -> set[str]:
        """Return every transitive predecessor of one Pipeline Activity."""

        ancestors: set[str] = set()
        pending = [item['activity_id'] for item in dependencies[activity_id]]
        while pending:
            candidate = pending.pop()
            if candidate in ancestors:
                continue
            ancestors.add(candidate)
            pending.extend(item['activity_id'] for item in dependencies[candidate])
        return ancestors

    @staticmethod
    def _is_human_child(child: ActivityRunDocument) -> bool:
        """Return whether an ActivityRun is completed by a human executor."""

        return child.activity_snapshot.get('executor') == 'human'

    @staticmethod
    def _requires_correction(child: ActivityRunDocument) -> bool:
        """Return whether a rejected human decision must rerun predecessors."""

        decision = child.execution_context.get('human_decision')
        return (
            child.activity_snapshot.get('executor') == 'human'
            and isinstance(decision, Mapping)
            and decision.get('decision') == 'rejected'
        )

    @staticmethod
    def _require_text(value: str) -> str:
        """Require non-empty user input and actor IDs."""

        normalized = value.strip()
        if not normalized:
            raise ValueError('Pipeline run input must not be empty.')
        return normalized
