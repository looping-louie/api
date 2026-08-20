"""Opaque HTTP entity tags for pipeline-run concurrency control."""

from hashlib import sha256

from src.app.models.pipeline_run import PipelineRunDocument


def pipeline_run_etag(document: PipelineRunDocument) -> str:
    """Return the strong entity tag for the current persisted run version."""

    digest = sha256(document.updated_at.isoformat().encode()).hexdigest()
    return f'"{digest}"'
