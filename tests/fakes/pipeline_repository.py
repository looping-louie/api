"""In-memory pipeline repository for service and router tests."""

from __future__ import annotations

from copy import deepcopy

from src.app.models.activity import ActivityChangelogEntry, ActivityDocument
from src.app.models.pipeline import (
    PipelineChangelogEntry,
    PipelineDetails,
    PipelineDocument,
    PipelineStatus,
)


class FakePipelineRepository:
    """Store pipeline documents and changelog entries in memory."""

    def __init__(self) -> None:
        """Initialize empty workspace-scoped stores."""

        self.documents: dict[tuple[str, str], PipelineDocument] = {}
        self.entries: list[PipelineChangelogEntry] = []
        self.activity_documents: list[ActivityDocument] = []
        self.activity_entries: list[ActivityChangelogEntry] = []

    async def list(
        self,
        *,
        workspace_id: str,
        offset: int,
        limit: int,
        status: PipelineStatus | None,
        search: str | None,
    ) -> tuple[list[PipelineDocument], int]:
        """Return one filtered deterministic page."""

        values = [
            deepcopy(document)
            for (current_workspace, _), document in self.documents.items()
            if current_workspace == workspace_id
            and (
                document.status == status
                if status is not None
                else document.status != "archived"
            )
            and (
                search is None
                or search.casefold() in document.name.casefold()
                or search.casefold() in document.description.casefold()
            )
        ]
        rank = {"active": 0, "disabled": 1, "archived": 2}
        values.sort(
            key=lambda document: (
                rank[document.status],
                -document.updated_at.timestamp(),
                document.id,
            )
        )
        return values[offset:offset + limit], len(values)

    async def get(
        self,
        *,
        workspace_id: str,
        pipeline_id: str,
    ) -> PipelineDocument | None:
        """Return one stored pipeline."""

        document = self.documents.get((workspace_id, pipeline_id))
        return deepcopy(document) if document is not None else None

    async def get_with_activities(
        self,
        *,
        workspace_id: str,
        pipeline_id: str,
    ) -> PipelineDetails | None:
        """Return one pipeline and its generated Activities in step order."""

        document = await self.get(
            workspace_id=workspace_id,
            pipeline_id=pipeline_id,
        )
        if document is None:
            return None
        activities_by_id = {
            activity.id: activity
            for activity in self.activity_documents
            if activity.workspace_id == workspace_id
        }
        return PipelineDetails(
            document=document,
            activities=tuple(
                deepcopy(activities_by_id[step.activity_id])
                for step in document.steps
            ),
        )

    async def create(
        self,
        *,
        document: PipelineDocument,
        changelog_entry: PipelineChangelogEntry,
    ) -> PipelineDocument:
        """Create a pipeline and append its first entry."""

        self.documents[(document.workspace_id, document.id)] = deepcopy(
            document
        )
        self.entries.append(deepcopy(changelog_entry))
        return deepcopy(document)

    async def create_with_activities(
        self,
        *,
        document: PipelineDocument,
        changelog_entry: PipelineChangelogEntry,
        activity_documents: list[ActivityDocument],
        activity_changelog_entries: list[ActivityChangelogEntry],
    ) -> PipelineDocument:
        """Create a pipeline with generated Activity records in memory."""

        self.activity_documents.extend(deepcopy(activity_documents))
        self.activity_entries.extend(deepcopy(activity_changelog_entries))
        return await self.create(
            document=document,
            changelog_entry=changelog_entry,
        )

    async def update(
        self,
        *,
        document: PipelineDocument,
        changelog_entry: PipelineChangelogEntry,
    ) -> bool:
        """Replace a pipeline and append its entry."""

        return self._replace(document, changelog_entry)

    async def update_with_activities(
        self,
        *,
        document: PipelineDocument,
        changelog_entry: PipelineChangelogEntry,
        activity_documents: list[ActivityDocument],
        activity_changelog_entries: list[ActivityChangelogEntry],
    ) -> bool:
        """Replace a pipeline and retain generated Activities in memory."""

        if (document.workspace_id, document.id) not in self.documents:
            return False
        self.activity_documents.extend(deepcopy(activity_documents))
        self.activity_entries.extend(deepcopy(activity_changelog_entries))
        return self._replace(document, changelog_entry)

    async def archive(
        self,
        *,
        document: PipelineDocument,
        changelog_entry: PipelineChangelogEntry,
    ) -> bool:
        """Archive a pipeline and append its entry."""

        return self._replace(document, changelog_entry)

    async def list_changelog(
        self,
        *,
        workspace_id: str,
        pipeline_id: str,
        offset: int,
        limit: int,
    ) -> tuple[list[PipelineChangelogEntry], int]:
        """Return newest entries for one pipeline."""

        values = [
            deepcopy(entry)
            for entry in self.entries
            if entry.workspace_id == workspace_id
            and entry.pipeline_id == pipeline_id
        ]
        values.reverse()
        return values[offset:offset + limit], len(values)

    def _replace(
        self,
        document: PipelineDocument,
        entry: PipelineChangelogEntry,
    ) -> bool:
        """Replace one existing document and retain its changelog."""

        key = (document.workspace_id, document.id)
        if key not in self.documents:
            return False
        self.documents[key] = deepcopy(document)
        self.entries.append(deepcopy(entry))
        return True
