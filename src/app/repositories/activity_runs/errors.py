"""Persistence conflicts raised by activity-run checkpoint transitions."""


class ActivityRunTokenConflictError(RuntimeError):
    """Raised when a continuation token is stale or does not match."""


class ActivityRunInvalidTransitionError(RuntimeError):
    """Raised when a checkpoint action cannot advance the current run."""
