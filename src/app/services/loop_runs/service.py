"""Application service for creating and reading loop runs."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from secrets import token_urlsafe
from typing import Callable, Mapping

from src.app.models.loop import LoopDocument
from src.app.models.loop_run import LoopRunDocument
from src.app.repositories.loop_runs.loop_run_repository import LoopRunRepository
from src.app.services.execution_instruction_library import (
    ExecutionInstructionLibraryService,
)
from src.app.services.loop_runs.generation import LoopRunGenerationService
from src.app.services.model_execution import ModelExecutionService
from src.app.services.loops.service import LoopService
from src.app.services.loops.types import LoopValidationError
from src.app.services.shared.pagination import PAGE_SIZE
from src.app.services.shared.tenant import TenantService


class LoopRunNotFoundError(Exception):
    """Raised when a loop run is absent from its parent loop."""

    def __init__(self, *, loop_id: str, run_id: str) -> None:
        """Store the parent loop and missing run identifiers."""

        super().__init__(f"Loop run '{run_id}' was not found for loop '{loop_id}'.")
        self.loop_id = loop_id
        self.run_id = run_id


class LoopRunUnavailableError(Exception):
    """Raised when a loop cannot start a new execution."""

    def __init__(self, *, loop_id: str, loop_status: str) -> None:
        """Store the loop state that prevents execution."""

        super().__init__(f"Loop '{loop_id}' with status '{loop_status}' cannot run.")
        self.loop_id = loop_id
        self.loop_status = loop_status


class LoopRunService:
    """Create loop execution records before checkpoint processing begins."""

    def __init__(
        self,
        *,
        repository: LoopRunRepository,
        loop_service: LoopService,
        tenant_service: TenantService,
        id_factory: Callable[[], str],
        token_factory: Callable[[], str] = lambda: token_urlsafe(32),
        model_execution_service: ModelExecutionService | None = None,
        instruction_library_service: ExecutionInstructionLibraryService | None = None,
        clock: Callable[[], datetime],
    ) -> None:
        """Store dependencies used to own and persist loop runs."""

        self._repository = repository
        self._loop_service = loop_service
        self._tenant_service = tenant_service
        self._id_factory = id_factory
        self._token_factory = token_factory
        self._clock = clock
        self._generation_service = (
            LoopRunGenerationService(
                model_execution_service=model_execution_service,
                instruction_library_service=instruction_library_service,
            )
            if model_execution_service is not None
            else None
        )

    async def create(
        self,
        *,
        user_id: str,
        loop_id: str,
        input_text: str,
        requested_workspace_id: str | None = None,
    ) -> LoopRunDocument:
        """Persist a loop run awaiting the CLI repository snapshot."""

        normalized_input = self._require_text(input_text, 'input')
        loop = await self._loop_service.get(
            user_id=user_id,
            loop_id=loop_id,
            requested_workspace_id=requested_workspace_id,
        )
        if loop.status != 'active':
            raise LoopRunUnavailableError(
                loop_id=loop.id,
                loop_status=loop.status,
            )
        workspace = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        now = self._clock()
        document = LoopRunDocument(
            id=self._id_factory(),
            workspace_id=workspace.workspace_id,
            loop_id=loop.id,
            input=normalized_input,
            status='in_progress',
            state='awaiting_snapshot',
            next_action='collect_snapshot',
            iteration=1,
            token_revision=0,
            continuation_token=self._token_factory(),
            loop_snapshot=self._snapshot(loop),
            execution_context={},
            created_at=now,
            created_by=self._require_text(user_id, 'user_id'),
            updated_at=now,
        )
        return await self._repository.create(document=document)

    async def continue_collect_snapshot(
        self,
        *,
        user_id: str,
        loop_id: str,
        run_id: str,
        continuation_token: str,
        idempotency_key: str,
        repo_context: str,
        workspace_path: str,
        source_commit_sha: str,
        constitution: str,
        project_profile: dict[str, object],
        requested_workspace_id: str | None = None,
    ) -> LoopRunDocument:
        """Generate loop operations after receiving CLI context."""

        workspace = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        context = {
            'repo_context': self._require_text(repo_context, 'repo_context'),
            'workspace_metadata': {
                'workspace_path': self._require_text(
                    workspace_path,
                    'workspace_path',
                ),
                'source_commit_sha': self._require_text(
                    source_commit_sha,
                    'source_commit_sha',
                ),
            },
            'constitution': constitution,
            'project_profile': project_profile,
        }
        document = await self.get(
            user_id=user_id,
            loop_id=loop_id,
            run_id=run_id,
            requested_workspace_id=requested_workspace_id,
        )
        previous_review = document.execution_context.get('review_result')
        if isinstance(previous_review, Mapping):
            context['review_result'] = dict(previous_review)
        if self._generation_service is None:
            return await self._repository.continue_collect_snapshot(
                workspace_id=workspace.workspace_id,
                loop_id=loop_id,
                run_id=run_id,
                continuation_token=continuation_token,
                idempotency_key=idempotency_key,
                execution_context=context,
                updated_at=self._clock(),
            )
        generation_service = self._require_generation_service()
        generation_service.require_executable_flow(document.loop_snapshot)
        context = await generation_service.generate_context(
            loop_snapshot=document.loop_snapshot,
            workspace_id=workspace.workspace_id,
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
            input_text=document.input,
            context=context,
        )
        return await self._repository.transition(
            workspace_id=workspace.workspace_id,
            loop_id=self._require_text(loop_id, 'loop_id'),
            run_id=self._require_text(run_id, 'run_id'),
            continuation_token=self._require_text(
                continuation_token,
                'continuation_token',
            ),
            idempotency_key=self._require_text(
                idempotency_key,
                'idempotency_key',
            ),
            expected_action='collect_snapshot',
            status='in_progress',
            state='awaiting_apply',
            next_action='apply_operations',
            next_continuation_token=self._token_factory(),
            execution_context=context,
            updated_at=self._clock(),
        )

    async def continue_action(
        self,
        *,
        user_id: str,
        loop_id: str,
        run_id: str,
        continuation_token: str,
        idempotency_key: str,
        action: str,
        result: Mapping[str, object],
        requested_workspace_id: str | None = None,
    ) -> LoopRunDocument:
        """Advance one executable loop CLI checkpoint."""

        document = await self.get(
            user_id=user_id,
            loop_id=loop_id,
            run_id=run_id,
            requested_workspace_id=requested_workspace_id,
        )
        self._require_generation_service().require_executable_flow(
            document.loop_snapshot,
        )
        workspace = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        context = dict(document.execution_context)
        if action == 'apply_operations':
            if result.get('applied') is not True:
                return await self._transition(
                    document=document,
                    workspace_id=workspace.workspace_id,
                    continuation_token=continuation_token,
                    idempotency_key=idempotency_key,
                    action=action,
                    status='failed',
                    state='failed',
                    next_action='none',
                    next_token=None,
                    context={**context, 'apply_result': dict(result)},
                )
            context['apply_result'] = dict(result)
            if self._has_reviewers(document.loop_snapshot):
                return await self._transition(
                    document=document,
                    workspace_id=workspace.workspace_id,
                    continuation_token=continuation_token,
                    idempotency_key=idempotency_key,
                    action=action,
                    status='in_progress',
                    state='awaiting_review_input',
                    next_action='submit_review_input',
                    next_token=self._token_factory(),
                    context=context,
                )
            return await self._transition(
                document=document,
                workspace_id=workspace.workspace_id,
                continuation_token=continuation_token,
                idempotency_key=idempotency_key,
                action=action,
                status='in_progress',
                state='awaiting_commit',
                next_action='commit_if_allowed',
                next_token=self._token_factory(),
                context=context,
            )
        if action == 'submit_review_input':
            review_context = await self._require_generation_service().generate_review_context(
                loop_snapshot=document.loop_snapshot,
                workspace_id=workspace.workspace_id,
                input_text=document.input,
                context=context,
                final_diff=str(result.get('final_diff', '')),
                changed_file_contents=self._changed_file_contents(result),
            )
            updated_context = {
                **context,
                'review_input': dict(result),
                'review_result': review_context,
            }
            approved = review_context['approved'] is True
            if not approved and document.iteration < self._max_iterations(
                document.loop_snapshot,
            ):
                return await self._transition(
                    document=document,
                    workspace_id=workspace.workspace_id,
                    continuation_token=continuation_token,
                    idempotency_key=idempotency_key,
                    action=action,
                    status='in_progress',
                    state='awaiting_snapshot',
                    next_action='collect_snapshot',
                    next_token=self._token_factory(),
                    context=updated_context,
                    iteration=document.iteration + 1,
                )
            return await self._transition(
                document=document,
                workspace_id=workspace.workspace_id,
                continuation_token=continuation_token,
                idempotency_key=idempotency_key,
                action=action,
                status='in_progress' if approved else 'failed',
                state='awaiting_commit' if approved else 'failed',
                next_action='commit_if_allowed' if approved else 'none',
                next_token=self._token_factory() if approved else None,
                context=updated_context,
            )
        if action == 'commit_if_allowed':
            committed = result.get('committed') is True
            return await self._transition(
                document=document,
                workspace_id=workspace.workspace_id,
                continuation_token=continuation_token,
                idempotency_key=idempotency_key,
                action=action,
                status='completed' if committed else 'failed',
                state='completed' if committed else 'failed',
                next_action='none',
                next_token=None,
                context={**context, 'commit_result': dict(result)},
            )
        raise LoopValidationError(field_name='result.action', message='is not supported')

    @staticmethod
    def _has_reviewers(snapshot: Mapping[str, object]) -> bool:
        """Return whether the persisted loop includes post-apply reviewers."""

        agents = snapshot.get('agents')
        return isinstance(agents, (list, tuple)) and any(
            isinstance(agent, Mapping) and agent.get('role') == 'reviewer'
            for agent in agents
        )

    @staticmethod
    def _changed_file_contents(
        result: Mapping[str, object],
    ) -> dict[str, str]:
        """Keep only validated CLI file contents for reviewer prompts."""

        contents = result.get('changed_file_contents')
        if not isinstance(contents, Mapping):
            return {}
        return {
            path: content
            for path, content in contents.items()
            if isinstance(path, str) and isinstance(content, str)
        }

    @staticmethod
    def _max_iterations(snapshot: Mapping[str, object]) -> int:
        """Return the validated loop iteration limit from its snapshot."""

        stop_conditions = snapshot.get('stop_conditions')
        max_iterations = (
            stop_conditions.get('max_iterations')
            if isinstance(stop_conditions, Mapping)
            else None
        )
        return max_iterations if isinstance(max_iterations, int) else 1

    async def _transition(
        self,
        *,
        document: LoopRunDocument,
        workspace_id: str,
        continuation_token: str,
        idempotency_key: str,
        action: str,
        status: str,
        state: str,
        next_action: str,
        next_token: str | None,
        context: dict[str, object],
        iteration: int | None = None,
    ) -> LoopRunDocument:
        """Persist a token-guarded continuation with a new runtime context."""

        return await self._repository.transition(
            workspace_id=workspace_id,
            loop_id=document.loop_id,
            run_id=document.id,
            continuation_token=continuation_token,
            idempotency_key=idempotency_key,
            expected_action=action,
            status=status,
            state=state,
            next_action=next_action,
            next_continuation_token=next_token,
            execution_context=context,
            updated_at=self._clock(),
            iteration=iteration,
        )

    async def get(
        self,
        *,
        user_id: str,
        loop_id: str,
        run_id: str,
        requested_workspace_id: str | None = None,
    ) -> LoopRunDocument:
        """Return a loop run after validating its parent loop visibility."""

        workspace = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        document = await self._repository.get(
            workspace_id=workspace.workspace_id,
            loop_id=self._require_text(loop_id, 'loop_id'),
            run_id=self._require_text(run_id, 'run_id'),
        )
        if document is None:
            raise LoopRunNotFoundError(loop_id=loop_id, run_id=run_id)
        return document

    async def list(
        self,
        *,
        user_id: str,
        loop_id: str,
        offset: int,
        requested_workspace_id: str | None = None,
    ) -> tuple[list[LoopRunDocument], int]:
        """Return one page of runs after validating the parent loop exists."""

        await self._loop_service.get(
            user_id=user_id,
            loop_id=loop_id,
            requested_workspace_id=requested_workspace_id,
        )
        workspace = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        if offset < 0:
            raise LoopValidationError(field_name='offset', message='must be positive')
        documents, total = await self._repository.list(
            workspace_id=workspace.workspace_id,
            loop_id=self._require_text(loop_id, 'loop_id'),
            offset=offset,
            limit=PAGE_SIZE,
        )
        return list(documents), total

    @staticmethod
    def _snapshot(loop: LoopDocument) -> dict[str, object]:
        """Capture the complete loop definition selected at run creation."""

        snapshot = asdict(loop)
        for field_name in ('created_at', 'updated_at'):
            snapshot[field_name] = snapshot[field_name].isoformat()
        return snapshot

    def _require_generation_service(self) -> LoopRunGenerationService:
        """Return model orchestration after confirming it is configured."""

        if self._generation_service is None:
            raise RuntimeError('Loop generation is not configured.')
        return self._generation_service

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        """Return a non-empty normalized string or raise a loop error."""

        normalized = value.strip()
        if not normalized:
            raise LoopValidationError(field_name=field_name, message='must not be empty')
        return normalized
