"""Application service for loop definitions and changelog access."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from src.app.models.loop import (
    LoopChangelogEntry,
    LoopDocument,
)
from src.app.repositories.loops.loop_repository import LoopRepository
from src.app.services.loops.mutation import (
    apply_patch,
    build_entry,
    change_type,
    changed_fields,
    normalize_flow,
    normalize_offset,
    require_patch_allowed,
)
from src.app.services.loops.types import (
    LoopCreate,
    LoopNotFoundError,
    LoopPatch,
    LoopValidationError,
)
from src.app.services.loops.validation import (
    document_content,
    normalize_agents,
    normalize_description,
    normalize_output_contract,
    normalize_stop_conditions,
    require_text,
    validate_loop,
)
from src.app.services.shared.reference_resolver import (
    ReferenceResolver,
    ResourceReference,
)
from src.app.services.shared.dependency_checker import DependencyChecker
from src.app.services.shared.tenant import TenantService
from src.app.services.shared.pagination import PAGE_SIZE


class LoopService:
    """Coordinate validated loop operations for one resolved workspace."""

    def __init__(
        self,
        *,
        repository: LoopRepository,
        tenant_service: TenantService,
        reference_resolver: ReferenceResolver,
        dependency_checker: DependencyChecker,
        id_factory: Callable[[], str],
        clock: Callable[[], datetime],
    ) -> None:
        """Store persistence, tenancy, reference, and generation dependencies."""

        self._repository = repository
        self._tenant_service = tenant_service
        self._reference_resolver = reference_resolver
        self._dependency_checker = dependency_checker
        self._id_factory = id_factory
        self._clock = clock

    async def list(
        self,
        *,
        user_id: str,
        offset: int,
        requested_workspace_id: str | None = None,
    ) -> tuple[list[LoopDocument], int]:
        """Return one fixed-size page of loops."""

        workspace_id = await self._workspace_id(
            user_id, requested_workspace_id
        )
        documents, total = await self._repository.list(
            workspace_id=workspace_id,
            offset=normalize_offset(offset),
            limit=PAGE_SIZE,
        )
        return list(documents), total

    async def get(
        self,
        *,
        user_id: str,
        loop_id: str,
        requested_workspace_id: str | None = None,
    ) -> LoopDocument:
        """Return one loop or raise the standard loop not-found error."""

        workspace_id = await self._workspace_id(
            user_id, requested_workspace_id
        )
        return await self._require_loop(workspace_id, loop_id)

    async def create(
        self,
        *,
        user_id: str,
        payload: LoopCreate,
        requested_workspace_id: str | None = None,
    ) -> LoopDocument:
        """Create a validated active loop and its initial changelog entry."""

        workspace_id = await self._workspace_id(
            user_id, requested_workspace_id
        )
        actor_id = require_text(user_id, "user_id")
        now = self._clock()
        document = LoopDocument(
            id=self._id_factory(),
            workspace_id=workspace_id,
            title=require_text(payload.title, "title"),
            description=normalize_description(payload.description),
            flow=normalize_flow(payload.flow),
            status="active",
            stop_conditions=normalize_stop_conditions(
                payload.stop_conditions
            ),
            agents=normalize_agents(payload.agents, self._id_factory),
            output_contract=normalize_output_contract(
                payload.output_contract
            ),
            created_at=now,
            created_by=actor_id,
            updated_at=now,
            updated_by=actor_id,
        )
        validate_loop(document)
        await self._validate_references(document)
        entry = build_entry(
            document=document,
            actor_id=actor_id,
            change_type="created",
            changed_at=now,
            entry_id=self._id_factory(),
            content=document_content(document),
        )
        return await self._repository.create(
            document=document,
            changelog_entry=entry,
        )

    async def patch(
        self,
        *,
        user_id: str,
        loop_id: str,
        payload: LoopPatch,
        requested_workspace_id: str | None = None,
    ) -> LoopDocument:
        """Apply supplied loop fields and append one precise changelog entry."""

        workspace_id = await self._workspace_id(
            user_id, requested_workspace_id
        )
        current = await self._require_loop(workspace_id, loop_id)
        require_patch_allowed(current, payload)
        actor_id = require_text(user_id, "user_id")
        updated = apply_patch(
            current,
            payload,
            actor_id=actor_id,
            id_factory=self._id_factory,
            changed_at=self._clock(),
        )
        validate_loop(updated)
        await self._validate_references(updated)
        diff = changed_fields(current, updated, payload.provided_fields)
        if not diff:
            raise LoopValidationError(
                field_name="body",
                message="must produce at least one effective change",
            )

        entry = build_entry(
            document=updated,
            actor_id=actor_id,
            change_type=change_type(current.status, updated.status),
            changed_at=updated.updated_at,
            entry_id=self._id_factory(),
            diff=diff,
        )
        if not await self._repository.update(
            document=updated,
            changelog_entry=entry,
        ):
            raise LoopNotFoundError(loop_id=loop_id)
        return updated

    async def delete(
        self,
        *,
        user_id: str,
        loop_id: str,
        requested_workspace_id: str | None = None,
    ) -> None:
        """Permanently delete a loop while retaining its final snapshot."""

        workspace_id = await self._workspace_id(
            user_id, requested_workspace_id
        )
        current = await self._require_loop(workspace_id, loop_id)
        await self._dependency_checker.require_deletable(
            workspace_id=workspace_id,
            target=ResourceReference("loop", current.id),
        )
        actor_id = require_text(user_id, "user_id")
        entry = build_entry(
            document=current,
            actor_id=actor_id,
            change_type="deleted",
            changed_at=self._clock(),
            entry_id=self._id_factory(),
            content=document_content(current),
        )
        if not await self._repository.delete(
            workspace_id=workspace_id,
            loop_id=current.id,
            changelog_entry=entry,
        ):
            raise LoopNotFoundError(loop_id=loop_id)

    async def list_changelog(
        self,
        *,
        user_id: str,
        loop_id: str,
        offset: int,
        requested_workspace_id: str | None = None,
    ) -> tuple[list[LoopChangelogEntry], int]:
        """Return retained changelog entries, including after loop deletion."""

        workspace_id = await self._workspace_id(
            user_id, requested_workspace_id
        )
        entries, total = await self._repository.list_changelog(
            workspace_id=workspace_id,
            loop_id=require_text(loop_id, "loop_id"),
            offset=normalize_offset(offset),
            limit=PAGE_SIZE,
        )
        if total == 0:
            raise LoopNotFoundError(loop_id=loop_id)
        return list(entries), total

    async def _validate_references(self, document: LoopDocument) -> None:
        """Require every selected persona and model to exist."""

        references = [
            reference
            for agent in document.agents
            for reference in (
                ResourceReference("model", agent.model_id),
                ResourceReference("persona", agent.persona_id),
            )
        ]
        await self._reference_resolver.require_many(
            workspace_id=document.workspace_id,
            references=references,
        )

    async def _require_loop(
        self,
        workspace_id: str,
        loop_id: str,
    ) -> LoopDocument:
        """Load one loop or raise a domain not-found error."""

        normalized_id = require_text(loop_id, "loop_id")
        document = await self._repository.get(
            workspace_id=workspace_id,
            loop_id=normalized_id,
        )
        if document is None:
            raise LoopNotFoundError(loop_id=normalized_id)
        return document

    async def _workspace_id(
        self,
        user_id: str,
        requested_workspace_id: str | None,
    ) -> str:
        """Resolve the workspace available to the authenticated user."""

        tenant = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        return tenant.workspace_id
