"""Application service for creating and reading loop runs."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from secrets import token_urlsafe
from typing import Callable

from src.app.models.loop import LoopDocument
from src.app.models.loop_run import LoopRunDocument
from src.app.repositories.loop_runs.loop_run_repository import LoopRunRepository
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
        clock: Callable[[], datetime],
    ) -> None:
        """Store dependencies used to own and persist loop runs."""

        self._repository = repository
        self._loop_service = loop_service
        self._tenant_service = tenant_service
        self._id_factory = id_factory
        self._token_factory = token_factory
        self._clock = clock

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
        return await self._repository.continue_collect_snapshot(
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
            execution_context=context,
            updated_at=self._clock(),
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

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        """Return a non-empty normalized string or raise a loop error."""

        normalized = value.strip()
        if not normalized:
            raise LoopValidationError(field_name=field_name, message='must not be empty')
        return normalized