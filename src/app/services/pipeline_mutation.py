"""Helpers for pipeline patches and useful changelog diffs."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import replace
from datetime import datetime

from src.app.models.changelog import JsonObject
from src.app.models.pipeline import PipelineDocument, PipelineStep
from src.app.services.pipeline_types import (
    InvalidPipelineStepsError,
    PipelineArchivedError,
    PipelinePatch,
)
from src.app.services.pipeline_validation import (
    document_content,
    normalize_description,
    normalize_steps,
    require_text,
    step_content,
)
from src.app.services.shared.changelog import changed_field_diff


def apply_patch(
    current: PipelineDocument,
    payload: PipelinePatch,
    *,
    actor_id: str,
    changed_at: datetime,
) -> PipelineDocument:
    """Build and validate the complete candidate after a partial update."""

    if not payload.provided_fields:
        raise InvalidPipelineStepsError(
            field_name="body",
            message="must contain at least one mutable field",
        )
    if current.status == "archived":
        raise PipelineArchivedError(pipeline_id=current.id)

    values: dict[str, object] = {}
    for field_name in payload.provided_fields:
        value = getattr(payload, field_name)
        if value is None:
            raise InvalidPipelineStepsError(
                field_name=field_name,
                message="must not be null",
            )
        values[field_name] = value

    if "title" in values:
        values["title"] = require_text(values["title"], "title")
    if "description" in values:
        values["description"] = normalize_description(
            values["description"]
        )
    if "enabled" in values:
        if not isinstance(values["enabled"], bool):
            raise InvalidPipelineStepsError(
                field_name="enabled",
                message="must be a boolean",
            )
        values["status"] = (
            "active" if values.pop("enabled") else "disabled"
        )
    if "steps" in values:
        values["steps"] = normalize_steps(values["steps"])

    return replace(
        current,
        **values,
        updated_at=changed_at,
        updated_by=actor_id,
    )


def changed_fields(
    before: PipelineDocument,
    after: PipelineDocument,
    fields: frozenset[str],
) -> JsonObject:
    """Build normal field changes plus position-aware step details."""

    old = document_content(before)
    new = document_content(after)
    diff = changed_field_diff(old, new, fields - {"steps"})
    if "steps" in fields and old["steps"] != new["steps"]:
        diff["steps"] = _step_diff(before.steps, after.steps)
    return diff


def _step_diff(
    before: tuple[PipelineStep, ...],
    after: tuple[PipelineStep, ...],
) -> JsonObject:
    """Compare step content by position and report stable reorder matches."""

    old = [step_content(step) for step in before]
    new = [step_content(step) for step in after]
    overlap = min(len(old), len(new))
    return {
        "from": old,
        "to": new,
        "added": [
            {"position": position, "step": new[position]}
            for position in range(len(old), len(new))
        ],
        "removed": [
            {"position": position, "step": old[position]}
            for position in range(len(new), len(old))
        ],
        "changed": [
            {
                "position": position,
                "from": old[position],
                "to": new[position],
            }
            for position in range(overlap)
            if old[position] != new[position]
        ],
        "order_changes": _order_changes(old, new),
    }


def _order_changes(
    before: list[JsonObject],
    after: list[JsonObject],
) -> list[JsonObject]:
    """Match duplicate serialized steps by occurrence and report movements."""

    old_positions: dict[str, list[int]] = defaultdict(list)
    new_positions: dict[str, list[int]] = defaultdict(list)
    for position, step in enumerate(before):
        old_positions[_step_key(step)].append(position)
    for position, step in enumerate(after):
        new_positions[_step_key(step)].append(position)

    changes: list[JsonObject] = []
    for key in old_positions.keys() & new_positions.keys():
        for old_position, new_position in zip(
            old_positions[key],
            new_positions[key],
        ):
            if old_position != new_position:
                changes.append(
                    {
                        "step": before[old_position],
                        "from": old_position,
                        "to": new_position,
                    }
                )
    changes.sort(key=lambda change: (change["from"], change["to"]))
    return changes


def _step_key(step: JsonObject) -> str:
    """Return deterministic serialized content for duplicate matching."""

    return json.dumps(step, sort_keys=True, separators=(",", ":"))
