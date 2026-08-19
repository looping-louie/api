"""Application service for activity-owned checkpoint execution."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from secrets import token_urlsafe
from typing import Mapping

from src.app.models.activity_run import ActivityRunDocument
from src.app.repositories.activity_runs.repository import ActivityRunRepository
from src.app.repositories.loop_runs.errors import LoopRunInvalidTransitionError
from src.app.services.activities.service import ActivityService
from src.app.services.activity_runs.types import ActivityRunUnavailableError
from src.app.services.execution_instructions import ExecutionInstructionLibraryService
from src.app.services.loop_runs.generation import LoopRunGenerationService
from src.app.services.loop_runs.types import LoopRunNotFoundError
from src.app.services.loops.types import LoopValidationError
from src.app.services.model_execution import ModelExecutionService
from src.app.services.shared.pagination import PAGE_SIZE
from src.app.services.shared.tenant import TenantService


class ActivityRunService:
    """Create and advance executions owned by active executable activities."""

    def __init__(
        self,
        *,
        repository: ActivityRunRepository,
        activity_service: ActivityService,
        tenant_service: TenantService,
        id_factory: Callable[[], str],
        clock: Callable[[], datetime],
        model_execution_service: ModelExecutionService | None = None,
        instruction_library_service: ExecutionInstructionLibraryService | None = None,
        token_factory: Callable[[], str] = lambda: token_urlsafe(32),
    ) -> None:
        """Store dependencies used to persist and generate activity runs."""

        self._repository = repository
        self._activity_service = activity_service
        self._tenant_service = tenant_service
        self._id_factory = id_factory
        self._clock = clock
        self._token_factory = token_factory
        self._generation_service = (
            LoopRunGenerationService(
                model_execution_service=model_execution_service,
                instruction_library_service=instruction_library_service,
            )
            if model_execution_service is not None
            and instruction_library_service is not None
            else None
        )

    async def create(
        self,
        *,
        user_id: str,
        activity_id: str,
        input_text: str,
        requested_workspace_id: str | None = None,
    ) -> ActivityRunDocument:
        """Persist a new run from an active executable activity."""

        activity = await self._active_activity(
            user_id=user_id,
            activity_id=activity_id,
            requested_workspace_id=requested_workspace_id,
        )
        workspace = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        now = self._clock()
        return await self._repository.create(
            document=ActivityRunDocument(
                id=self._id_factory(),
                workspace_id=workspace.workspace_id,
                activity_id=activity.id,
                input=self._require_text(input_text, 'input'),
                status='in_progress',
                state='awaiting_snapshot',
                next_action='collect_snapshot',
                iteration=1,
                token_revision=0,
                continuation_token=self._token_factory(),
                activity_snapshot=self._snapshot(activity),
                execution_context={},
                created_at=now,
                created_by=self._require_text(user_id, 'user_id'),
                updated_at=now,
            )
        )

    async def get(
        self,
        *,
        user_id: str,
        activity_id: str,
        run_id: str,
        requested_workspace_id: str | None = None,
    ) -> ActivityRunDocument:
        """Return one run after validating activity ownership."""

        workspace = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        document = await self._repository.get(
            workspace_id=workspace.workspace_id,
            activity_id=activity_id,
            run_id=run_id,
        )
        if document is None:
            raise LoopRunNotFoundError(loop_id=activity_id, run_id=run_id)
        return document

    async def list(
        self,
        *,
        user_id: str,
        activity_id: str,
        offset: int,
        requested_workspace_id: str | None = None,
    ) -> tuple[list[ActivityRunDocument], int]:
        """Return a page of runs for an active executable activity."""

        await self._active_activity(
            user_id=user_id,
            activity_id=activity_id,
            requested_workspace_id=requested_workspace_id,
        )
        if offset < 0:
            raise LoopValidationError(field_name='offset', message='must be positive')
        workspace = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        documents, total = await self._repository.list(
            workspace_id=workspace.workspace_id,
            activity_id=activity_id,
            offset=offset,
            limit=PAGE_SIZE,
        )
        return list(documents), total

    async def continue_run(
        self,
        *,
        user_id: str,
        activity_id: str,
        run_id: str,
        pipeline_run_id: str | None,
        lease_token: str | None,
        continuation_token: str,
        idempotency_key: str,
        action: str,
        result: Mapping[str, object],
        requested_workspace_id: str | None = None,
    ) -> ActivityRunDocument:
        """Advance one validated CLI checkpoint for an activity run."""

        await self._active_activity(
            user_id=user_id,
            activity_id=activity_id,
            requested_workspace_id=requested_workspace_id,
        )
        document = await self.get(
            user_id=user_id,
            activity_id=activity_id,
            run_id=run_id,
            requested_workspace_id=requested_workspace_id,
        )
        workspace = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        if not await self._repository.has_active_pipeline_lease(
            workspace_id=workspace.workspace_id,
            activity_run_id=document.id,
            pipeline_run_id=pipeline_run_id,
            lease_token=lease_token,
            now=self._clock(),
        ):
            raise LoopRunInvalidTransitionError()
        context = dict(document.execution_context)
        if action == 'collect_snapshot':
            previous_review = context.get('review_result')
            context = dict(result)
            context.pop('action', None)
            if isinstance(previous_review, Mapping):
                context['review_result'] = dict(previous_review)
            if self._generation_service is None:
                return await self._transition(
                    document=document, workspace_id=workspace.workspace_id,
                    pipeline_run_id=pipeline_run_id, lease_token=lease_token,
                    continuation_token=continuation_token, idempotency_key=idempotency_key,
                    action=action, status='in_progress', state='awaiting_generation',
                    next_action='none', next_token=None, context=context,
                )
            generated = await self._generation_service.generate_context(
                loop_snapshot=document.activity_snapshot,
                workspace_id=workspace.workspace_id,
                user_id=user_id,
                requested_workspace_id=requested_workspace_id,
                input_text=document.input,
                context=context,
            )
            return await self._transition(
                document=document, workspace_id=workspace.workspace_id,
                pipeline_run_id=pipeline_run_id, lease_token=lease_token,
                continuation_token=continuation_token, idempotency_key=idempotency_key,
                action=action, status='in_progress', state='awaiting_apply',
                next_action='apply_operations', next_token=self._token_factory(),
                context=generated,
            )
        if action == 'apply_operations':
            context['apply_result'] = dict(result)
            applied = result.get('applied') is True
            return await self._transition(
                document=document, workspace_id=workspace.workspace_id,
                pipeline_run_id=pipeline_run_id, lease_token=lease_token,
                continuation_token=continuation_token, idempotency_key=idempotency_key,
                action=action, status='in_progress' if applied else 'failed',
                state='awaiting_review_input' if applied and self._has_reviewers(document.activity_snapshot)
                else ('awaiting_commit' if applied else 'failed'),
                next_action='submit_review_input' if applied and self._has_reviewers(document.activity_snapshot)
                else ('commit_if_allowed' if applied else 'none'),
                next_token=self._token_factory() if applied else None, context=context,
            )
        if action == 'submit_review_input':
            if self._generation_service is None:
                raise RuntimeError('Activity generation is not configured.')
            review = await self._generation_service.generate_review_context(
                loop_snapshot=document.activity_snapshot,
                workspace_id=workspace.workspace_id,
                input_text=document.input,
                context=context,
                final_diff=str(result.get('final_diff', '')),
                changed_file_contents=self._changed_files(result),
            )
            updated_context = {**context, 'review_input': dict(result), 'review_result': review}
            approved = review['approved'] is True
            retry = not approved and document.iteration < self._max_iterations(document.activity_snapshot)
            return await self._transition(
                document=document, workspace_id=workspace.workspace_id,
                pipeline_run_id=pipeline_run_id, lease_token=lease_token,
                continuation_token=continuation_token, idempotency_key=idempotency_key,
                action=action, status='in_progress' if approved or retry else 'failed',
                state='awaiting_commit' if approved else ('awaiting_snapshot' if retry else 'failed'),
                next_action='commit_if_allowed' if approved else ('collect_snapshot' if retry else 'none'),
                next_token=self._token_factory() if approved or retry else None,
                context=updated_context, iteration=document.iteration + 1 if retry else None,
            )
        if action == 'commit_if_allowed':
            committed = result.get('committed') is True
            return await self._transition(
                document=document, workspace_id=workspace.workspace_id,
                pipeline_run_id=pipeline_run_id, lease_token=lease_token,
                continuation_token=continuation_token, idempotency_key=idempotency_key,
                action=action, status='completed' if committed else 'failed',
                state='completed' if committed else 'failed', next_action='none',
                next_token=None, context={**context, 'commit_result': dict(result)},
            )
        raise LoopValidationError(field_name='result.action', message='is not supported')

    async def _transition(
        self,
        *,
        document: ActivityRunDocument,
        workspace_id: str,
        pipeline_run_id: str | None,
        lease_token: str | None,
        continuation_token: str,
        idempotency_key: str,
        action: str,
        status: str,
        state: str,
        next_action: str,
        next_token: str | None,
        context: dict[str, object],
        iteration: int | None = None,
    ) -> ActivityRunDocument:
        """Persist a token-guarded activity-run state transition."""

        return await self._repository.transition(
            workspace_id=workspace_id, activity_id=document.activity_id,
            run_id=document.id, pipeline_run_id=pipeline_run_id,
            lease_token=lease_token, continuation_token=continuation_token,
            idempotency_key=idempotency_key, expected_action=action, status=status,
            state=state, next_action=next_action, next_continuation_token=next_token,
            execution_context=context, updated_at=self._clock(), iteration=iteration,
        )

    async def _active_activity(
        self, *, user_id: str, activity_id: str, requested_workspace_id: str | None,
    ) -> object:
        """Return an active activity that has an executable configuration."""

        activity = await self._activity_service.get(
            user_id=user_id, activity_id=activity_id,
            requested_workspace_id=requested_workspace_id,
        )
        if activity.type not in (
            'direct_loop',
            'refinement_loop',
            'roundtable_loop',
        ):
            raise ActivityRunUnavailableError(activity_id=activity.id, reason='type is not executable')
        if activity.status != 'active':
            raise ActivityRunUnavailableError(activity_id=activity.id, reason='status is not active')
        return activity

    @staticmethod
    def _snapshot(activity: object) -> dict[str, object]:
        """Shape an activity configuration for the shared generation engine."""

        flow = {
            'direct_loop': 'direct',
            'refinement_loop': 'refinement',
            'roundtable_loop': 'roundtable',
        }
        return {
            'id': getattr(activity, 'id'),
            'title': getattr(activity, 'name'),
            'description': getattr(activity, 'description'),
            **dict(getattr(activity, 'config')),
            'flow': flow[getattr(activity, 'type')],
        }

    @staticmethod
    def _has_reviewers(snapshot: Mapping[str, object]) -> bool:
        """Return whether an activity snapshot configures reviewer agents."""

        agents = snapshot.get('agents')
        return isinstance(agents, (list, tuple)) and any(
            isinstance(agent, Mapping) and agent.get('role') == 'reviewer'
            for agent in agents
        )

    @staticmethod
    def _max_iterations(snapshot: Mapping[str, object]) -> int:
        """Return the validated iteration limit from the activity snapshot."""

        conditions = snapshot.get('stop_conditions')
        value = conditions.get('max_iterations') if isinstance(conditions, Mapping) else None
        return value if isinstance(value, int) else 1

    @staticmethod
    def _changed_files(result: Mapping[str, object]) -> dict[str, str]:
        """Keep valid changed file contents for reviewer generation."""

        contents = result.get('changed_file_contents')
        if not isinstance(contents, Mapping):
            return {}
        return {path: content for path, content in contents.items() if isinstance(path, str) and isinstance(content, str)}

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        """Return a non-empty text value or raise the shared validation error."""

        normalized = value.strip()
        if not normalized:
            raise LoopValidationError(field_name=field_name, message='must not be empty')
        return normalized
