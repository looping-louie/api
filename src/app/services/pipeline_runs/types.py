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

    def __init__(
        self,
        *,
        pipeline_id: str,
        reason: str,
        reason_code: str | None = None,
        activity_id: str | None = None,
        model_id: str | None = None,
    ) -> None:
        """Store the pipeline state that prevents execution."""

        super().__init__(f"Pipeline '{pipeline_id}' cannot run: {reason}.")
        self.pipeline_id = pipeline_id
        self.reason = reason
        self.reason_code = reason_code
        self.activity_id = activity_id
        self.model_id = model_id


class PipelineRunPreconditionFailedError(Exception):
    """Raised when a conditional pipeline-run claim observes stale state."""

    def __init__(self, *, pipeline_id: str, run_id: str) -> None:
        """Store the run whose previously observed version is no longer current."""

        super().__init__(f"Pipeline run '{run_id}' no longer matches the supplied ETag.")
        self.pipeline_id = pipeline_id
        self.run_id = run_id
