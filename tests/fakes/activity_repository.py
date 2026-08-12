"""In-memory activity repository for service and route tests."""

from __future__ import annotations

from copy import deepcopy

from src.app.models.activity import ActivityChangelogEntry, ActivityDocument


class FakeActivityRepository:
    """Store activities and changelog entries in memory."""

    def __init__(self) -> None:
        """Initialize empty workspace-scoped stores."""

        self.documents: dict[tuple[str, str], ActivityDocument] = {}
        self.entries: list[ActivityChangelogEntry] = []

    async def list(self, *, workspace_id: str, offset: int, limit: int) -> tuple[list[ActivityDocument], int]:
        """Return one deterministic activity page."""

        values = [deepcopy(document) for (current_workspace, _), document in self.documents.items() if current_workspace == workspace_id]
        values.sort(key=lambda document: (-document.updated_at.timestamp(), document.id))
        return values[offset:offset + limit], len(values)

    async def get(self, *, workspace_id: str, activity_id: str) -> ActivityDocument | None:
        """Return one stored activity."""

        document = self.documents.get((workspace_id, activity_id))
        return deepcopy(document) if document is not None else None

    async def create(self, *, document: ActivityDocument, changelog_entry: ActivityChangelogEntry) -> ActivityDocument:
        """Create an activity and append its first entry."""

        self.documents[(document.workspace_id, document.id)] = deepcopy(document)
        self.entries.append(deepcopy(changelog_entry))
        return deepcopy(document)

    async def update(self, *, document: ActivityDocument, changelog_entry: ActivityChangelogEntry) -> bool:
        """Replace an activity and append its entry."""

        key = (document.workspace_id, document.id)
        if key not in self.documents:
            return False
        self.documents[key] = deepcopy(document)
        self.entries.append(deepcopy(changelog_entry))
        return True

    async def delete(self, *, workspace_id: str, activity_id: str, changelog_entry: ActivityChangelogEntry) -> bool:
        """Delete an activity and retain its entry."""

        key = (workspace_id, activity_id)
        if key not in self.documents:
            return False
        self.entries.append(deepcopy(changelog_entry))
        del self.documents[key]
        return True

    async def list_changelog(self, *, workspace_id: str, activity_id: str, offset: int, limit: int) -> tuple[list[ActivityChangelogEntry], int]:
        """Return newest entries for one activity."""

        values = [deepcopy(entry) for entry in self.entries if entry.workspace_id == workspace_id and entry.activity_id == activity_id]
        values.reverse()
        return values[offset:offset + limit], len(values)
