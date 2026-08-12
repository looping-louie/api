"""Persistence contract for activities and their immutable changelog."""

from __future__ import annotations

from typing import Protocol, Sequence

from src.app.models.activity import ActivityChangelogEntry, ActivityDocument


class ActivityRepository(Protocol):
    """Persistence operations required by the activity service."""

    async def list(self, *, workspace_id: str, offset: int, limit: int) -> tuple[Sequence[ActivityDocument], int]:
        """Return one page of activities and the unpaginated total."""
        ...

    async def get(self, *, workspace_id: str, activity_id: str) -> ActivityDocument | None:
        """Return one activity when it exists in the workspace."""
        ...

    async def create(self, *, document: ActivityDocument, changelog_entry: ActivityChangelogEntry) -> ActivityDocument:
        """Create an activity and its changelog entry atomically."""
        ...

    async def update(self, *, document: ActivityDocument, changelog_entry: ActivityChangelogEntry) -> bool:
        """Replace an activity and append its changelog entry atomically."""
        ...

    async def delete(self, *, workspace_id: str, activity_id: str, changelog_entry: ActivityChangelogEntry) -> bool:
        """Delete an activity and append its final changelog entry atomically."""
        ...

    async def list_changelog(self, *, workspace_id: str, activity_id: str, offset: int, limit: int) -> tuple[Sequence[ActivityChangelogEntry], int]:
        """Return one newest-first changelog page and its total."""
        ...