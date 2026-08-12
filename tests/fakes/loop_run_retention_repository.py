"""In-memory retained-run lookup for loop deletion tests."""


class FakeLoopRunRetentionRepository:
    """Track loop identifiers that have retained run history."""

    def __init__(self) -> None:
        """Initialize the empty retained-run collection."""

        self.loop_ids: set[tuple[str, str]] = set()

    async def has_runs(
        self,
        *,
        workspace_id: str,
        loop_id: str,
    ) -> bool:
        """Return whether the selected loop has a retained run."""

        return (workspace_id, loop_id) in self.loop_ids
