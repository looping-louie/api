"""Persistence conflicts raised by loop-run checkpoint transitions."""


class LoopRunTokenConflictError(RuntimeError):
    """Raised when a continuation token is stale or does not match."""


class LoopRunInvalidTransitionError(RuntimeError):
    """Raised when a checkpoint action cannot advance the current run."""