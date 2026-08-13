"""Persistence contract required by the pipeline service."""

from __future__ import annotations

from typing import Protocol, Sequence

from src.app.models.activity import ActivityChangelogEntry, ActivityDocument
from src.app.models.pipeline import (
    PipelineChangelogEntry,
    PipelineDetails,
    PipelineDocument,
    PipelineStatus,
)


class PipelineRepository(Protocol):
    """Store workspace-scoped pipelines and immutable changelogs."""

    async def list(
        self,
        *,
        workspace_id: str,
        offset: int,
        limit: int,
        status: PipelineStatus | None,
        search: str | None,
    ) -> tuple[Sequence[PipelineDocument], int]:
        """Return one filtered page and its total."""

        ...

    async def get(
        self,
        *,
        workspace_id: str,
        pipeline_id: str,
    ) -> PipelineDocument | None:
        """Return one pipeline if present."""

        ...

    async def get_with_activities(
        self,
        *,
        workspace_id: str,
        pipeline_id: str,
    ) -> PipelineDetails | None:
        """Return one pipeline and its ordered Activity documents."""

        ...

    async def create(
        self,
        *,
        document: PipelineDocument,
        changelog_entry: PipelineChangelogEntry,
    ) -> PipelineDocument:
        """Create a pipeline and its first changelog entry."""

        ...

    async def create_with_activities(
        self,
        *,
        document: PipelineDocument,
        changelog_entry: PipelineChangelogEntry,
        activity_documents: Sequence[ActivityDocument],
        activity_changelog_entries: Sequence[ActivityChangelogEntry],
    ) -> PipelineDocument:
        """Atomically create a pipeline and its generated activities."""

        ...

    async def update(
        self,
        *,
        document: PipelineDocument,
        changelog_entry: PipelineChangelogEntry,
    ) -> bool:
        """Replace mutable pipeline data and append one entry."""

        ...

    async def update_with_activities(
        self,
        *,
        document: PipelineDocument,
        changelog_entry: PipelineChangelogEntry,
        activity_documents: Sequence[ActivityDocument],
        activity_changelog_entries: Sequence[ActivityChangelogEntry],
    ) -> bool:
        """Atomically replace a pipeline and persist generated activities."""

        ...

    async def archive(
        self,
        *,
        document: PipelineDocument,
        changelog_entry: PipelineChangelogEntry,
    ) -> bool:
        """Archive a pipeline and append one entry."""

        ...

    async def list_changelog(
        self,
        *,
        workspace_id: str,
        pipeline_id: str,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[PipelineChangelogEntry], int]:
        """Return newest-first changelog entries."""

        ...
