"""Application service for creating and reading loop runs."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from secrets import token_urlsafe
import json
from typing import Callable, Mapping

from src.app.models.loop import LoopDocument
from src.app.models.loop_run import LoopRunDocument
from src.app.repositories.loop_runs.loop_run_repository import LoopRunRepository
from src.app.services.loops.service import LoopService
from src.app.services.loops.types import LoopValidationError
from src.app.services.shared.pagination import PAGE_SIZE
from src.app.services.shared.tenant import TenantService
from src.app.services.model_execution import ModelExecutionError, ModelExecutionService


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
        clock: Callable[[], datetime],
    ) -> None:
        """Store dependencies used to own and persist loop runs."""

        self._repository = repository
        self._loop_service = loop_service
        self._tenant_service = tenant_service
        self._id_factory = id_factory
        self._token_factory = token_factory
        self._clock = clock
        self._model_execution_service = model_execution_service

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
        """Persist CLI local context and advance to API generation readiness."""

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
        document = await self.get(user_id=user_id, loop_id=loop_id, run_id=run_id, requested_workspace_id=requested_workspace_id)
        if self._model_execution_service is None:
            return await self._repository.continue_collect_snapshot(
                workspace_id=workspace.workspace_id, loop_id=loop_id, run_id=run_id,
                continuation_token=continuation_token, idempotency_key=idempotency_key,
                execution_context=context, updated_at=self._clock(),
            )
        context = await self._generate_context(
            loop_snapshot=document.loop_snapshot, workspace_id=workspace.workspace_id,
            input_text=document.input, context=context,
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
        self, *, user_id: str, loop_id: str, run_id: str, continuation_token: str,
        idempotency_key: str, action: str, result: Mapping[str, object],
        requested_workspace_id: str | None = None,
    ) -> LoopRunDocument:
        """Advance one CLI-owned loop checkpoint and execute reviews when due."""

        document = await self.get(user_id=user_id, loop_id=loop_id, run_id=run_id, requested_workspace_id=requested_workspace_id)
        workspace = await self._tenant_service.resolve(user_id=user_id, requested_workspace_id=requested_workspace_id)
        context = dict(document.execution_context)
        if action == 'apply_operations':
            if result.get('applied') is not True:
                return await self._transition(document, workspace.workspace_id, continuation_token, idempotency_key, action, 'failed', 'failed', 'none', None, {**context, 'apply_result': dict(result)})
            context['apply_result'] = dict(result)
            has_reviewers = any(agent.get('role') == 'reviewer' for agent in self._agents(document.loop_snapshot))
            next_action = 'submit_review_input' if has_reviewers else 'commit_if_allowed'
            next_state = 'awaiting_review_input' if has_reviewers else 'awaiting_commit'
            return await self._transition(document, workspace.workspace_id, continuation_token, idempotency_key, action, 'in_progress', next_state, next_action, self._token_factory(), context)
        if action == 'submit_review_input':
            context['review_input'] = dict(result)
            approved = await self._review(document=document, context=context)
            context['review_approved'] = approved
            return await self._transition(document, workspace.workspace_id, continuation_token, idempotency_key, action, 'in_progress' if approved else 'failed', 'awaiting_commit' if approved else 'failed', 'commit_if_allowed' if approved else 'none', self._token_factory() if approved else None, context)
        if action == 'commit_if_allowed':
            committed = result.get('committed') is True
            return await self._transition(document, workspace.workspace_id, continuation_token, idempotency_key, action, 'completed' if committed else 'failed', 'completed' if committed else 'failed', 'none', None, {**context, 'commit_result': dict(result)})
        raise LoopValidationError(field_name='result.action', message='is not supported')

    async def _transition(self, document: LoopRunDocument, workspace_id: str, token: str, key: str, action: str, status: str, state: str, next_action: str, next_token: str | None, context: dict[str, object]) -> LoopRunDocument:
        """Persist a token-guarded continuation with a new runtime context."""

        return await self._repository.transition(workspace_id=workspace_id, loop_id=document.loop_id, run_id=document.id, continuation_token=token, idempotency_key=key, expected_action=action, status=status, state=state, next_action=next_action, next_continuation_token=next_token, execution_context=context, updated_at=self._clock())

    async def _generate_context(self, *, loop_snapshot: Mapping[str, object], workspace_id: str, input_text: str, context: dict[str, object]) -> dict[str, object]:
        """Run configured generators and store the operation plan for CLI application."""

        agents = [agent for agent in self._agents(loop_snapshot) if agent.get('role') == 'generator']
        outputs = [await self._execute_agent(workspace_id, agent, f'{input_text}\n\n{context["repo_context"]}') for agent in agents]
        if not outputs:
            raise LoopValidationError(field_name='agents', message='requires a generator')
        flow = str(loop_snapshot.get('flow'))
        generated = outputs[0] if flow != 'roundtable' else await self._aggregate(workspace_id, loop_snapshot, outputs, input_text)
        return {**context, 'runtime_artifacts': {'generator_outputs': outputs, 'operations': generated.get('operations', []), 'commit_message': generated.get('commit_message')}}

    async def _aggregate(self, workspace_id: str, snapshot: Mapping[str, object], outputs: list[dict[str, object]], input_text: str) -> dict[str, object]:
        """Use the configured roundtable aggregator to synthesize one operation set."""

        aggregators = [agent for agent in self._agents(snapshot) if agent.get('role') == 'aggregator']
        if not aggregators:
            raise LoopValidationError(field_name='agents', message='roundtable requires an aggregator')
        return await self._execute_agent(workspace_id, aggregators[0], f'{input_text}\n\nCandidate operation sets:\n{json.dumps(outputs)}')

    async def _review(self, *, document: LoopRunDocument, context: dict[str, object]) -> bool:
        """Require every configured reviewer to explicitly approve the local diff."""

        reviewers = [agent for agent in self._agents(document.loop_snapshot) if agent.get('role') == 'reviewer']
        if not reviewers:
            return True
        review_input = context['review_input']
        return all((await self._execute_agent(document.workspace_id, agent, json.dumps(review_input))).get('approved') is True for agent in reviewers)

    async def _execute_agent(self, workspace_id: str, agent: Mapping[str, object], prompt: str) -> dict[str, object]:
        """Execute one configured agent and require a JSON object response."""

        if self._model_execution_service is None:
            raise ModelExecutionError('Model execution is not configured.')
        result = await self._model_execution_service.execute(workspace_id=workspace_id, model_id=str(agent['model_id']), prompt=prompt)
        try:
            payload = json.loads(result.text)
        except json.JSONDecodeError as error:
            raise ModelExecutionError('Loop agent returned invalid JSON.') from error
        if not isinstance(payload, dict):
            raise ModelExecutionError('Loop agent response must be a JSON object.')
        return payload

    @staticmethod
    def _agents(snapshot: Mapping[str, object]) -> list[Mapping[str, object]]:
        """Return serialized loop agents as mapping values only."""

        agents = snapshot.get('agents')
        return [agent for agent in agents if isinstance(agent, Mapping)] if isinstance(agents, list) else []

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

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        """Return a non-empty normalized string or raise a loop error."""

        normalized = value.strip()
        if not normalized:
            raise LoopValidationError(field_name=field_name, message='must not be empty')
        return normalized