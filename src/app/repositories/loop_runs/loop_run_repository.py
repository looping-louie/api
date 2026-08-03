"""Persistence contract for loop execution records."""

from __future__ import annotations

from typing import Protocol, Sequence

from src.app.models.loop_run import LoopRunDocument


class LoopRunRepository(Protocol):
    """Persistence operations required by the loop-run service."""

    async def create(self, *, document: LoopRunDocument) -> LoopRunDocument:
        """Persist one newly created loop run."""
        raise NotImplementedError

    async def get(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        run_id: str,
    ) -> LoopRunDocument | None:
        """Return one loop run within its parent loop."""
        raise NotImplementedError

    async def list(
        self,
        *,
        workspace_id: str,
        loop_id: str,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[LoopRunDocument], int]:
        """Return one page of loop runs and its unpaginated total."""
        raise NotImplementedError