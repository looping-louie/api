"""Application errors for pipeline execution operations."""


class PipelineRunNotFoundError(Exception):
    """Raised when a pipeline run is absent from its parent pipeline."""

    def __init__(self, *, pipeline_id: str, run_id: str) -> None:
        """Store the pipeline and missing run identifiers."""

        super().__init__(f"Pipeline run '{run_id}' was not found for pipeline '{pipeline_id}'.")
        self.pipeline_id = pipeline_id
        self.run_id = run_id


class PipelineRunUnavailableError(Exception):
    """Raised when a pipeline cannot start an executable run."""

    def __init__(self, *, pipeline_id: str, reason: str) -> None:
        """Store the pipeline state that prevents execution."""

        super().__init__(f"Pipeline '{pipeline_id}' cannot run: {reason}.")
        self.pipeline_id = pipeline_id
        self.reason = reason


class PipelineRunPreconditionFailedError(Exception):
    """Raised when a conditional pipeline-run claim observes stale state."""

    def __init__(self, *, pipeline_id: str, run_id: str) -> None:
        """Store the run whose previously observed version is no longer current."""

        super().__init__(f"Pipeline run '{run_id}' no longer matches the supplied ETag.")
        self.pipeline_id = pipeline_id
        self.run_id = run_id


class PipelineRunGateNotFoundError(Exception):
    """Raised when a Pipeline run does not contain the requested gate."""

    def __init__(self, *, pipeline_id: str, run_id: str, activity_id: str) -> None:
        """Store the scoped run and requested gate identifiers."""

        super().__init__(
            f"Pipeline run '{run_id}' has no human gate for Activity "
            f"'{activity_id}'."
        )
        self.pipeline_id = pipeline_id
        self.run_id = run_id
        self.activity_id = activity_id


class PipelineRunGateUnavailableError(Exception):
    """Raised when a human gate cannot receive its requested transition."""

    def __init__(
        self,
        *,
        pipeline_id: str,
        run_id: str,
        activity_id: str,
        reason: str,
    ) -> None:
        """Store the scoped gate and reason the transition is unavailable."""

        super().__init__(
            f"Pipeline run '{run_id}' gate '{activity_id}' is unavailable: "
            f"{reason}."
        )
        self.pipeline_id = pipeline_id
        self.run_id = run_id
        self.activity_id = activity_id
        self.reason = reason
