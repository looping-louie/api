"""Detail builders for pipeline-specific API errors."""

from __future__ import annotations

from typing import Any


ErrorDetails = dict[str, Any]


def pipeline_details(error: Exception) -> ErrorDetails:
    """Return the pipeline identity carried by a pipeline error."""

    return {
        "resource_type": "pipeline",
        "resource_id": getattr(error, "pipeline_id"),
    }


def pipeline_run_unavailable_details(error: Exception) -> ErrorDetails:
    """Return the actionable reason that prevented PipelineRun creation."""

    details: ErrorDetails = {
        'resource_type': 'pipeline',
        'resource_id': getattr(error, 'pipeline_id'),
        'reason': getattr(error, 'reason_code', None),
    }
    for field_name in ('activity_id', 'model_id'):
        value = getattr(error, field_name, None)
        if value is not None:
            details[field_name] = value
    return details


def unsupported_step_details(error: Exception) -> ErrorDetails:
    """Return the rejected pipeline step discriminator."""

    return {
        "type": getattr(error, "step_type"),
    }


def unsupported_gate_details(error: Exception) -> ErrorDetails:
    """Return the rejected human gate discriminator."""

    return {
        "gate_type": getattr(error, "gate_type"),
    }
