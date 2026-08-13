"""Application service for pipeline definitions and changelog access."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Callable, cast

from src.app.models.activity import (
    ActivityChangelogEntry,
    ActivityDocument,
    ActivityType,
)
from src.app.models.pipeline import (
    PipelineChangelogEntry,
    PipelineDocument,
    PipelineActivityStep,
)
from src.app.repositories.pipelines.repository import (
    PipelineRepository,
)
from src.app.services.pipelines.operations import (
    build_entry,
    change_type,
    normalize_offset,
    normalize_search,
    require_pipeline,
)
from src.app.services.pipelines.mutation import (
    apply_patch,
    changed_fields,
)
from src.app.services.pipelines.types import (
    InvalidPipelineStepsError,
    PipelineArchivedError,
    PipelineActivityInput,
    PipelineCreate,
    PipelineNotFoundError,
    PipelinePatch,
)
from src.app.services.pipelines.validation import (
    document_content,
    normalize_description,
    normalize_status,
    normalize_steps,
    require_text,
)
from src.app.services.shared.changelog import changed_field_diff
from src.app.services.shared.pagination import PAGE_SIZE
from src.app.services.shared.tenant import TenantService


class PipelineService:
    """Coordinate validated pipeline operations for one workspace."""

    def __init__(
        self,
        *,
        repository: PipelineRepository,
        tenant_service: TenantService,
        id_factory: Callable[[], str],
        clock: Callable[[], datetime],
    ) -> None:
        """Store persistence, tenancy, and generated-value dependencies."""

        self._repository = repository
        self._tenant_service = tenant_service
        self._id_factory = id_factory
        self._clock = clock

    async def list(
        self,
        *,
        user_id: str,
        offset: int,
        status: str | None = None,
        search: str | None = None,
        requested_workspace_id: str | None = None,
    ) -> tuple[list[PipelineDocument], int]:
        """Return one filtered fixed-size pipeline page."""

        workspace_id = await self._workspace_id(
            user_id,
            requested_workspace_id,
        )
        documents, total = await self._repository.list(
            workspace_id=workspace_id,
            offset=normalize_offset(offset),
            limit=PAGE_SIZE,
            status=(
                normalize_status(status)
                if status is not None
                else None
            ),
            search=normalize_search(search),
        )
        return list(documents), total

    async def get(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        requested_workspace_id: str | None = None,
    ) -> PipelineDocument:
        """Return one complete pipeline."""

        workspace_id = await self._workspace_id(
            user_id,
            requested_workspace_id,
        )
        return await require_pipeline(
            self._repository,
            workspace_id=workspace_id,
            pipeline_id=pipeline_id,
        )

    async def create(
        self,
        *,
        user_id: str,
        payload: PipelineCreate,
        requested_workspace_id: str | None = None,
    ) -> PipelineDocument:
        """Create an enabled validated pipeline and its initial changelog."""

        workspace_id = await self._workspace_id(
            user_id,
            requested_workspace_id,
        )
        actor_id = require_text(user_id, "user_id")
        now = self._clock()
        document = PipelineDocument(
            id=self._id_factory(),
            workspace_id=workspace_id,
            title=require_text(payload.title, "title"),
            description=normalize_description(payload.description),
            status="active",
            steps=(),
            created_at=now,
            created_by=actor_id,
            updated_at=now,
            updated_by=actor_id,
        )
        activities, activity_entries = self._build_activities(
            workspace_id=workspace_id,
            actor_id=actor_id,
            inputs=normalize_steps(payload.steps),
            now=now,
        )
        document = replace(
            document,
            steps=tuple(
                PipelineActivityStep(activity_id=activity.id)
                for activity in activities
            ),
        )
        entry = build_entry(
            id_factory=self._id_factory,
            document=document,
            actor_id=actor_id,
            entry_change_type="created",
            changed_at=now,
            content=document_content(document),
        )
        return await self._repository.create_with_activities(
            document=document,
            changelog_entry=entry,
            activity_documents=activities,
            activity_changelog_entries=activity_entries,
        )

    async def patch(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        payload: PipelinePatch,
        requested_workspace_id: str | None = None,
    ) -> PipelineDocument:
        """Apply a partial update after validating the resulting pipeline."""

        workspace_id = await self._workspace_id(
            user_id,
            requested_workspace_id,
        )
        current = await require_pipeline(
            self._repository,
            workspace_id=workspace_id,
            pipeline_id=pipeline_id,
        )
        actor_id = require_text(user_id, "user_id")
        activities: list[ActivityDocument] = []
        activity_entries: list[ActivityChangelogEntry] = []
        generated_steps = None
        if payload.steps is not None:
            activities, activity_entries = self._build_activities(
                workspace_id=workspace_id,
                actor_id=actor_id,
                inputs=normalize_steps(payload.steps),
                now=self._clock(),
            )
            generated_steps = tuple(
                PipelineActivityStep(activity_id=activity.id)
                for activity in activities
            )
        updated = apply_patch(
            current,
            payload,
            actor_id=actor_id,
            changed_at=self._clock(),
            steps=generated_steps,
        )
        diff = changed_fields(current, updated, payload.provided_fields)
        if not diff:
            raise InvalidPipelineStepsError(
                field_name="body",
                message="must produce at least one effective change",
            )
        entry = build_entry(
            id_factory=self._id_factory,
            document=updated,
            actor_id=actor_id,
            entry_change_type=change_type(current.status, updated.status),
            changed_at=updated.updated_at,
            diff=diff,
        )
        updated_persisted = (
            await self._repository.update_with_activities(
                document=updated,
                changelog_entry=entry,
                activity_documents=activities,
                activity_changelog_entries=activity_entries,
            )
            if activities
            else await self._repository.update(
                document=updated,
                changelog_entry=entry,
            )
        )
        if not updated_persisted:
            raise PipelineNotFoundError(pipeline_id=pipeline_id)
        return updated

    async def archive(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        requested_workspace_id: str | None = None,
    ) -> None:
        """Archive a pipeline instead of physically deleting it."""

        workspace_id = await self._workspace_id(
            user_id,
            requested_workspace_id,
        )
        current = await require_pipeline(
            self._repository,
            workspace_id=workspace_id,
            pipeline_id=pipeline_id,
        )
        if current.status == "archived":
            raise PipelineArchivedError(pipeline_id=current.id)
        actor_id = require_text(user_id, "user_id")
        archived = replace(
            current,
            status="archived",
            updated_at=self._clock(),
            updated_by=actor_id,
        )
        diff = changed_field_diff(
            document_content(current),
            document_content(archived),
            frozenset({"enabled", "status"}),
        )
        entry = build_entry(
            id_factory=self._id_factory,
            document=archived,
            actor_id=actor_id,
            entry_change_type="archived",
            changed_at=archived.updated_at,
            diff=diff,
        )
        if not await self._repository.archive(
            document=archived,
            changelog_entry=entry,
        ):
            raise PipelineNotFoundError(pipeline_id=pipeline_id)

    async def list_changelog(
        self,
        *,
        user_id: str,
        pipeline_id: str,
        offset: int,
        requested_workspace_id: str | None = None,
    ) -> tuple[list[PipelineChangelogEntry], int]:
        """Return newest-first pipeline changelog entries."""

        workspace_id = await self._workspace_id(
            user_id,
            requested_workspace_id,
        )
        normalized_id = require_text(pipeline_id, "pipeline_id")
        entries, total = await self._repository.list_changelog(
            workspace_id=workspace_id,
            pipeline_id=normalized_id,
            offset=normalize_offset(offset),
            limit=PAGE_SIZE,
        )
        if total == 0:
            raise PipelineNotFoundError(pipeline_id=normalized_id)
        return list(entries), total

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

    def _build_activities(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        inputs: tuple[PipelineActivityInput, ...],
        now: datetime,
    ) -> tuple[list[ActivityDocument], list[ActivityChangelogEntry]]:
        """Create independent active Activity documents for inline steps."""

        documents: list[ActivityDocument] = []
        entries: list[ActivityChangelogEntry] = []
        for position, value in enumerate(inputs):
            if value.type not in {
                "approval",
                "quiz",
                "direct_loop",
                "refinement_loop",
                "roundtable_loop",
            }:
                raise InvalidPipelineStepsError(
                    field_name=f"steps.{position}.type",
                    message="must contain a supported activity type",
                )
            document = ActivityDocument(
                id=self._id_factory(),
                workspace_id=workspace_id,
                title=value.title,
                description=value.description,
                status="active",
                type=cast(ActivityType, value.type),
                config=value.config,
                created_at=now,
                created_by=actor_id,
                updated_at=now,
                updated_by=actor_id,
            )
            documents.append(document)
            entries.append(
                ActivityChangelogEntry(
                    id=self._id_factory(),
                    activity_id=document.id,
                    workspace_id=workspace_id,
                    change_type="created",
                    actor_id=actor_id,
                    changed_at=now,
                    diff=None,
                    content={
                        "title": document.title,
                        "description": document.description,
                        "status": document.status,
                        "type": document.type,
                        "config": document.config,
                    },
                )
            )
        return documents, entries
