"""Application contracts and errors for activity-run operations."""

from __future__ import annotations


class ActivityRunNotFoundError(Exception):
    """Raised when an activity run is absent from its parent activity."""

    def __init__(self, *, activity_id: str, run_id: str) -> None:
        """Store the parent activity and missing run identifiers."""

        super().__init__(
            f"Activity run '{run_id}' was not found for activity "
            f"'{activity_id}'."
        )
        self.activity_id = activity_id
        self.run_id = run_id


class ActivityRunValidationError(Exception):
    """Raised when an activity-run input is invalid."""

    def __init__(self, *, field_name: str, message: str) -> None:
        """Store a field-specific validation failure."""

        super().__init__(
            f"Invalid activity-run field '{field_name}': {message}"
        )
        self.field_name = field_name
        self.message = message


class ActivityRunUnavailableError(Exception):
    """Raised when an activity cannot start or access an execution."""

    def __init__(self, *, activity_id: str, reason: str) -> None:
        """Store the activity state that prevents execution."""

        super().__init__(f"Activity '{activity_id}' cannot run: {reason}.")
        self.activity_id = activity_id
        self.reason = reason
