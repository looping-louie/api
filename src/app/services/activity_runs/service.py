"""Application service for activity-owned checkpoint execution."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from secrets import token_urlsafe
from typing import Mapping

from src.app.models.activity_run import ActivityRunDocument
from src.app.repositories.activity_runs.repository import ActivityRunRepository
from src.app.repositories.activity_runs.errors import (
    ActivityRunInvalidTransitionError,
)
from src.app.services.activities.service import ActivityService
from src.app.services.activity_runs.types import (
    ActivityRunNotFoundError,
    ActivityRunUnavailableError,
    ActivityRunValidationError,
)
from src.app.services.execution_instructions import ExecutionInstructionLibraryService
from src.app.services.activity_runs.generation import (
    ActivityRunGenerationService,
)
from src.app.services.models import ModelExecutionService
from src.app.services.models.availability import ModelServiceError
from src.app.services.shared.pagination import PAGE_SIZE
from src.app.services.shared.tenant import TenantService
from src.app.services.users import UserService
from src.app.services.projects.service import ProjectService


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
        workspace_service: ProjectService | None = None,
        user_service: UserService | None = None,
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
            ActivityRunGenerationService(
                model_execution_service=model_execution_service,
                instruction_library_service=instruction_library_service,
            )
            if model_execution_service is not None
            and instruction_library_service is not None
            else None
        )
        self._model_execution_service = model_execution_service
        self._workspace_service = workspace_service
        self._user_service = user_service

    async def create(
        self,
        *,
        user_id: str,
        activity_id: str,
        input_text: str,
        requested_workspace_id: str | None = None,
    ) -> ActivityRunDocument:
        """Persist a new run from an active Activity definition."""

        activity = await self._active_activity(
            user_id=user_id,
            activity_id=activity_id,
        )
        workspace = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        harness = await self._inherited_harness(
            activity=activity,
            user_id=user_id,
        )
        now = self._clock()
        return await self._repository.create(
            document=ActivityRunDocument(
                id=self._id_factory(),
                workspace_id=workspace.workspace_id,
                activity_id=activity.id,
                input=self._require_text(input_text, 'input'),
                status='in_progress',
                state=self._initial_state(activity),
                next_action=self._initial_action(activity),
                iteration=1,
                token_revision=0,
                continuation_token=self._token_factory(),
                activity_snapshot=await self._snapshot(
                    activity,
                    workspace_id=workspace.workspace_id,
                    user_id=user_id,
                    harness=harness,
                ),
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
            raise ActivityRunNotFoundError(
                activity_id=activity_id,
                run_id=run_id,
            )
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
        )
        if offset < 0:
            raise ActivityRunValidationError(
                field_name='offset',
                message='must be positive',
            )
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
        """Advance one validated runtime or human execution checkpoint."""

        await self._active_activity(
            user_id=user_id,
            activity_id=activity_id,
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
        human_execution = document.activity_snapshot.get('executor') == 'human'
        if not human_execution and not await self._repository.has_active_pipeline_lease(
            workspace_id=workspace.workspace_id,
            activity_run_id=document.id,
            pipeline_run_id=pipeline_run_id,
            lease_token=lease_token,
            now=self._clock(),
        ):
            raise ActivityRunInvalidTransitionError()
        if action == 'submit_human_decision':
            decision = str(result.get('decision'))
            return await self._transition(
                document=document,
                workspace_id=workspace.workspace_id,
                pipeline_run_id=pipeline_run_id,
                lease_token=lease_token,
                continuation_token=continuation_token,
                idempotency_key=idempotency_key,
                action=action,
                status='completed' if decision == 'approved' else 'failed',
                state='completed' if decision == 'approved' else 'failed',
                next_action='none',
                next_token=None,
                context={
                    **dict(document.execution_context),
                    'human_decision': dict(result),
                },
            )
        context = dict(document.execution_context)
        if action == 'collect_snapshot':
            previous_review = context.get('review_result')
            context = dict(result)
            context.pop('action', None)
            if isinstance(previous_review, Mapping):
                context['review_result'] = dict(previous_review)
            if self._uses_codex_cli(document.activity_snapshot):
                return await self._transition(
                    document=document, workspace_id=workspace.workspace_id,
                    pipeline_run_id=pipeline_run_id, lease_token=lease_token,
                    continuation_token=continuation_token, idempotency_key=idempotency_key,
                    action=action, status='in_progress', state='awaiting_harness',
                    next_action='run_harness', next_token=self._token_factory(),
                    context=context,
                )
            if self._generation_service is None:
                return await self._transition(
                    document=document, workspace_id=workspace.workspace_id,
                    pipeline_run_id=pipeline_run_id, lease_token=lease_token,
                    continuation_token=continuation_token, idempotency_key=idempotency_key,
                    action=action, status='in_progress', state='awaiting_generation',
                    next_action='none', next_token=None, context=context,
                )
            try:
                generated = await self._generation_service.generate_context(
                    loop_snapshot=document.activity_snapshot,
                    user_id=user_id,
                    requested_workspace_id=requested_workspace_id,
                    input_text=document.input,
                    context=context,
                )
            except ModelServiceError as error:
                return await self._generation_failure_transition(
                    document=document,
                    workspace_id=workspace.workspace_id,
                    pipeline_run_id=pipeline_run_id,
                    lease_token=lease_token,
                    continuation_token=continuation_token,
                    idempotency_key=idempotency_key,
                    action=action,
                    context=context,
                    error=error,
                )
            return await self._transition(
                document=document, workspace_id=workspace.workspace_id,
                pipeline_run_id=pipeline_run_id, lease_token=lease_token,
                continuation_token=continuation_token, idempotency_key=idempotency_key,
                action=action, status='in_progress', state='awaiting_apply',
                next_action='apply_operations', next_token=self._token_factory(),
                context=generated,
            )
        if action in ('apply_operations', 'run_harness'):
            context['apply_result' if action == 'apply_operations' else 'harness_result'] = dict(result)
            applied = result.get('applied') is True if action == 'apply_operations' else result.get('completed') is True
            commit_forbidden = document.activity_snapshot.get('commit_mode') == 'forbid'
            return await self._transition(
                document=document, workspace_id=workspace.workspace_id,
                pipeline_run_id=pipeline_run_id, lease_token=lease_token,
                continuation_token=continuation_token, idempotency_key=idempotency_key,
                action=action,
                status=(
                    'completed' if applied and commit_forbidden
                    and not self._has_reviewers(document.activity_snapshot)
                    else ('in_progress' if applied else 'failed')
                ),
                state=(
                    'awaiting_review_input' if applied and self._has_reviewers(document.activity_snapshot)
                    else ('completed' if applied and commit_forbidden else ('awaiting_commit' if applied else 'failed'))
                ),
                next_action=(
                    'submit_review_input' if applied and self._has_reviewers(document.activity_snapshot)
                    else ('none' if applied and commit_forbidden else ('commit_if_allowed' if applied else 'none'))
                ),
                next_token=(
                    self._token_factory() if applied and (
                        self._has_reviewers(document.activity_snapshot) or not commit_forbidden
                    ) else None
                ),
                context=context,
            )
        if action == 'submit_review_input':
            if self._generation_service is None:
                raise RuntimeError('Activity generation is not configured.')
            review = await self._generation_service.generate_review_context(
                loop_snapshot=document.activity_snapshot,
                input_text=document.input,
                context=context,
                final_diff=str(result.get('final_diff', '')),
                changed_file_contents=self._changed_files(result),
            )
            updated_context = {**context, 'review_input': dict(result), 'review_result': review}
            approved = review['approved'] is True
            retry = not approved and document.iteration < self._max_iterations(document.activity_snapshot)
            commit_forbidden = document.activity_snapshot.get('commit_mode') == 'forbid'
            return await self._transition(
                document=document, workspace_id=workspace.workspace_id,
                pipeline_run_id=pipeline_run_id, lease_token=lease_token,
                continuation_token=continuation_token, idempotency_key=idempotency_key,
                action=action,
                status=(
                    'completed' if approved and commit_forbidden
                    else ('in_progress' if approved or retry else 'failed')
                ),
                state=(
                    'completed' if approved and commit_forbidden
                    else ('awaiting_commit' if approved else ('awaiting_snapshot' if retry else 'failed'))
                ),
                next_action=(
                    'none' if approved and commit_forbidden
                    else ('commit_if_allowed' if approved else ('collect_snapshot' if retry else 'none'))
                ),
                next_token=self._token_factory() if (approved and not commit_forbidden) or retry else None,
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
        raise ActivityRunValidationError(
            field_name='result.action',
            message='is not supported',
        )

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

    async def _generation_failure_transition(
        self,
        *,
        document: ActivityRunDocument,
        workspace_id: str,
        pipeline_run_id: str | None,
        lease_token: str | None,
        continuation_token: str,
        idempotency_key: str,
        action: str,
        context: dict[str, object],
        error: ModelServiceError,
    ) -> ActivityRunDocument:
        """Persist an API-owned model configuration failure for the active claim."""

        return await self._transition(
            document=document,
            workspace_id=workspace_id,
            pipeline_run_id=pipeline_run_id,
            lease_token=lease_token,
            continuation_token=continuation_token,
            idempotency_key=idempotency_key,
            action=action,
            status='failed',
            state='failed',
            next_action='none',
            next_token=None,
            context={
                **context,
                'failure': {
                    'source': 'api',
                    'type': type(error).__name__,
                    'message': str(error),
                },
            },
        )

    async def _active_activity(
        self, *, user_id: str, activity_id: str,
    ) -> object:
        """Return an active Activity supported by the execution protocol."""

        activity = await self._activity_service.get(
            user_id=user_id, activity_id=activity_id,
        )
        if activity.type not in ('approval', 'quiz', 'direct_loop', 'refinement_loop', 'roundtable_loop'):
            raise ActivityRunUnavailableError(activity_id=activity.id, reason='type is not executable')
        if activity.status != 'active':
            raise ActivityRunUnavailableError(activity_id=activity.id, reason='status is not active')
        return activity

    async def _inherited_harness(
        self,
        *,
        activity: object,
        user_id: str,
    ) -> Mapping[str, object]:
        """Resolve Activity and User Harness overrides in order."""

        activity_harness = getattr(activity, 'harness')
        if activity_harness is not None:
            return self._harness_value(activity_harness)
        if self._user_service is not None:
            default_harness = (
                await self._user_service.get(user_id=user_id)
            ).settings.default_harness
            if default_harness is not None:
                return self._harness_value(default_harness)
        return {'kind': 'louie', 'version': 'v1', 'config': {}}

    @staticmethod
    def _harness_value(harness: object) -> Mapping[str, object]:
        """Convert a validated domain Harness into its frozen representation."""

        return {
            'kind': getattr(harness, 'kind'),
            'version': getattr(harness, 'version'),
            'config': dict(getattr(harness, 'config')),
        }

    async def _snapshot(
        self,
        activity: object,
        *,
        workspace_id: str,
        user_id: str,
        harness: Mapping[str, object],
    ) -> dict[str, object]:
        """Shape a frozen configuration for its assigned ActivityRun executor."""

        flow = {
            'direct_loop': 'direct',
            'refinement_loop': 'refinement',
            'roundtable_loop': 'roundtable',
        }
        config = dict(getattr(activity, 'config'))
        if harness.get('kind') == 'louie':
            inherited_model_id = await self._inherited_model_id(
                activity=activity,
                user_id=user_id,
            )
            agents = config.get('agents')
            if isinstance(agents, list):
                config['agents'] = [
                    await self._louie_agent_snapshot(
                        agent=agent,
                        activity_id=str(getattr(activity, 'id')),
                        workspace_id=workspace_id,
                        user_id=user_id,
                        inherited_model_id=inherited_model_id,
                    )
                    if isinstance(agent, dict)
                    else agent
                    for agent in agents
                ]
        snapshot = {
            'id': getattr(activity, 'id'),
            'title': getattr(activity, 'name'),
            'description': getattr(activity, 'description'),
            'harness': dict(harness),
            **config,
        }
        activity_type = getattr(activity, 'type')
        if activity_type in ('approval', 'quiz'):
            return {**snapshot, 'type': activity_type, 'executor': 'human'}
        return {**snapshot, 'flow': flow[activity_type], 'executor': 'runtime'}

    async def _inherited_model_id(
        self,
        *,
        activity: object,
        user_id: str,
    ) -> str | None:
        """Resolve the direct Activity model override and User fallback."""

        model_id = getattr(activity, 'model_id')
        if isinstance(model_id, str):
            return model_id
        if self._user_service is None:
            return None
        return (await self._user_service.get(user_id=user_id)).settings.default_model_id

    async def _louie_agent_snapshot(
        self,
        *,
        agent: dict[str, object],
        activity_id: str,
        workspace_id: str,
        user_id: str,
        inherited_model_id: str | None,
    ) -> dict[str, object]:
        """Freeze an available linked service for one Louie agent model."""

        snapshot = dict(agent)
        model_id = snapshot.get('model_id')
        if not isinstance(model_id, str):
            model_id = inherited_model_id
        if not isinstance(model_id, str):
            raise ActivityRunUnavailableError(
                activity_id=activity_id,
                reason='louie execution requires a model_id',
            )
        if self._model_execution_service is None:
            raise RuntimeError('Louie model execution is not configured.')
        linked_service = await self._model_execution_service.select_linked_service(
            workspace_id=workspace_id,
            model_id=model_id,
            user_id=user_id,
        )
        snapshot['model_target'] = {
            'linked_service_id': linked_service.id,
            'linked_service_user_id': linked_service.user_id,
            'model_id': model_id,
        }
        return snapshot

    @staticmethod
    def _initial_state(activity: object) -> str:
        """Return the first checkpoint state for the Activity's executor."""

        return (
            'awaiting_human_decision'
            if getattr(activity, 'type') in ('approval', 'quiz')
            else 'awaiting_snapshot'
        )

    @staticmethod
    def _initial_action(activity: object) -> str:
        """Return the first action expected from the Activity's executor."""

        return (
            'submit_human_decision'
            if getattr(activity, 'type') in ('approval', 'quiz')
            else 'collect_snapshot'
        )

    @staticmethod
    def _has_reviewers(snapshot: Mapping[str, object]) -> bool:
        """Return whether an activity snapshot configures reviewer agents."""

        agents = snapshot.get('agents')
        return isinstance(agents, (list, tuple)) and any(
            isinstance(agent, Mapping) and agent.get('role') == 'reviewer'
            for agent in agents
        )

    @staticmethod
    def _uses_codex_cli(snapshot: Mapping[str, object]) -> bool:
        """Return whether this direct-loop snapshot must run through Codex CLI."""

        harness = snapshot.get('harness')
        return (
            snapshot.get('flow') == 'direct'
            and isinstance(harness, Mapping)
            and harness.get('kind') == 'codex_cli'
            and harness.get('version') == 'v1'
            and harness.get('config') == {}
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
            raise ActivityRunValidationError(
                field_name=field_name,
                message='must not be empty',
            )
        return normalized
