"""In-memory loop repository for service tests."""

from __future__ import annotations

from copy import deepcopy

from src.app.models.loop import LoopChangelogEntry, LoopDocument


class FakeLoopRepository:
    """Store loops and changelog entries in memory."""

    def __init__(self) -> None:
        """Initialize empty workspace-scoped stores."""

        self.documents: dict[tuple[str, str], LoopDocument] = {}
        self.entries: list[LoopChangelogEntry] = []

    async def list(
        self,
        *,
        workspace_id: str,
        offset: int,
        limit: int,
    ) -> tuple[list[LoopDocument], int]:
        """Return one deterministic loop page."""

        values = [
            deepcopy(document)
            for (current_workspace, _), document in self.documents.items()
            if current_workspace == workspace_id
        ]
        values.sort(
            key=lambda document: (
                -document.updated_at.timestamp(),
                document.id,
            )
        )
        return values[offset:offset + limit], len(values)

    async def get(
        self,
        *,
        workspace_id: str,
        loop_id: str,
    ) -> LoopDocument | None:
        """Return one stored loop."""

        document = self.documents.get((workspace_id, loop_id))
        return deepcopy(document) if document is not None else None

    async def create(
        self,
        *,
        document: LoopDocument,
        changelog_entry: LoopChangelogEntry,
    ) -> LoopDocument:
        """Create a loop and append its first entry."""

        self.documents[(document.workspace_id, document.id)] = deepcopy(
            document
        )
        self.entries.append(deepcopy(changelog_entry))
        return deepcopy(document)

    async def update(
        self,
        *,
        document: LoopDocument,
        changelog_entry: LoopChangelogEntry,
    ) -> bool:
        """Replace a loop and append its entry."""

        key = (document.workspace_id, document.id)
        if key not in self.documents:
            return False
        self.documents[key] = deepcopy(document)
        self.entries.append(deepcopy(changelog_entry))
        return True

    async def delete(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        changelog_entry: LoopChangelogEntry,
    ) -> bool:
        """Delete a loop and retain its entry."""

        key = (workspace_id, loop_id)
        if key not in self.documents:
            return False
        self.entries.append(deepcopy(changelog_entry))
        del self.documents[key]
        return True

    async def list_changelog(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        offset: int,
        limit: int,
    ) -> tuple[list[LoopChangelogEntry], int]:
        """Return newest entries for one loop."""

        values = [
            deepcopy(entry)
            for entry in self.entries
            if entry.workspace_id == workspace_id
            and entry.loop_id == loop_id
        ]
        values.reverse()
        return values[offset:offset + limit], len(values)
