"""Application errors for activity-owned execution operations."""


class ActivityRunUnavailableError(Exception):
    """Raised when an activity cannot start or access an execution."""

    def __init__(self, *, activity_id: str, reason: str) -> None:
        """Store the activity state that prevents execution."""

        super().__init__(f"Activity '{activity_id}' cannot run: {reason}.")
        self.activity_id = activity_id
        self.reason = reason
