"""Persistence contract for loops and their immutable changelog."""

from __future__ import annotations

from typing import Protocol, Sequence

from src.app.models.loop import LoopChangelogEntry, LoopDocument


class LoopRepository(Protocol):
    """Persistence operations required by the loop service."""

    async def list(
        self,
        *,
        workspace_id: str,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[LoopDocument], int]:
        """Return one page of loops and the unpaginated total."""
        ...

    async def get(
        self,
        *,
        workspace_id: str,
        loop_id: str,
    ) -> LoopDocument | None:
        """Return one loop when it exists in the workspace."""
        ...

    async def create(
        self,
        *,
        document: LoopDocument,
        changelog_entry: LoopChangelogEntry,
    ) -> LoopDocument:
        """Create a loop and its changelog entry atomically."""
        ...

    async def update(
        self,
        *,
        document: LoopDocument,
        changelog_entry: LoopChangelogEntry,
    ) -> bool:
        """Replace a loop and append its changelog entry atomically."""
        ...

    async def delete(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        changelog_entry: LoopChangelogEntry,
    ) -> bool:
        """Delete a loop and append its final changelog entry atomically."""
        ...

    async def list_changelog(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[LoopChangelogEntry], int]:
        """Return one newest-first changelog page and its total."""
        ...
