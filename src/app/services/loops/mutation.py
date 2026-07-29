"""Helpers for constructing loop updates and changelog data."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Callable

from src.app.models.loop import (
    JsonObject,
    LoopChangelogEntry,
    LoopDocument,
    LoopFlow,
    LoopStatus,
)
from src.app.services.loops.types import (
    ArchivedLoopImmutableError,
    LoopPatch,
    LoopValidationError,
)
from src.app.services.loops.validation import (
    document_content,
    normalize_agents,
    normalize_description,
    normalize_output_contract,
    normalize_stop_conditions,
    require_text,
)
from src.app.services.shared.changelog import (
    build_changelog_metadata,
    changed_field_diff,
)
from src.app.services.shared.pagination import require_offset


def apply_patch(
    current: LoopDocument,
    payload: LoopPatch,
    *,
    actor_id: str,
    id_factory: Callable[[], str],
    changed_at: datetime,
) -> LoopDocument:
    """Build the complete candidate needed for aggregate validation."""

    values: dict[str, object] = {}
    for field_name in payload.provided_fields:
        value = getattr(payload, field_name)
        if value is None:
            raise LoopValidationError(
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
    if "flow" in values:
        values["flow"] = normalize_flow(values["flow"])
    if "status" in values:
        values["status"] = normalize_status(values["status"])
    if "stop_conditions" in values:
        values["stop_conditions"] = normalize_stop_conditions(
            values["stop_conditions"]
        )
    if "agents" in values:
        values["agents"] = normalize_agents(values["agents"], id_factory)
    if "output_contract" in values:
        values["output_contract"] = normalize_output_contract(
            values["output_contract"]
        )

    return replace(
        current,
        **values,
        updated_at=changed_at,
        updated_by=actor_id,
    )


def require_patch_allowed(
    current: LoopDocument,
    payload: LoopPatch,
) -> None:
    """Allow archived loops to receive only an active status."""

    if not payload.provided_fields:
        raise LoopValidationError(
            field_name="body",
            message="must contain at least one mutable field",
        )
    if current.status == "archived" and not (
        payload.provided_fields == {"status"}
        and payload.status == "active"
    ):
        raise ArchivedLoopImmutableError(loop_id=current.id)


def build_entry(
    *,
    document: LoopDocument,
    actor_id: str,
    change_type: str,
    changed_at: datetime,
    entry_id: str,
    diff: JsonObject | None = None,
    content: JsonObject | None = None,
) -> LoopChangelogEntry:
    """Build one generated changelog entry."""

    metadata = build_changelog_metadata(
        entry_id=entry_id,
        workspace_id=document.workspace_id,
        actor_id=actor_id,
        changed_at=changed_at,
        diff=diff,
        content=content,
    )
    return LoopChangelogEntry(
        id=metadata.id,
        loop_id=document.id,
        workspace_id=metadata.workspace_id,
        change_type=change_type,  # type: ignore[arg-type]
        actor_id=metadata.actor_id,
        changed_at=metadata.changed_at,
        diff=metadata.diff,
        content=metadata.content,
    )


def changed_fields(
    before: LoopDocument,
    after: LoopDocument,
    fields: frozenset[str],
) -> JsonObject:
    """Return only effective changes using JSON-compatible values."""

    old = document_content(before)
    new = document_content(after)
    return changed_field_diff(old, new, fields)


def change_type(before: LoopStatus, after: LoopStatus) -> str:
    """Select the specific status event or a normal update event."""

    if before == after:
        return "updated"
    return {
        "active": "enabled",
        "disabled": "disabled",
        "archived": "archived",
    }[after]


def normalize_flow(value: object) -> LoopFlow:
    """Validate one supported flow."""

    if value not in {"direct", "refinement", "roundtable"}:
        raise LoopValidationError(
            field_name="flow",
            message="must be direct, refinement, or roundtable",
        )
    return value  # type: ignore[return-value]


def normalize_status(value: object) -> LoopStatus:
    """Validate one supported status."""

    if value not in {"active", "disabled", "archived"}:
        raise LoopValidationError(
            field_name="status",
            message="must be active, disabled, or archived",
        )
    return value  # type: ignore[return-value]


def normalize_offset(value: object) -> int:
    """Translate shared offset validation to the loop error contract."""

    try:
        return require_offset(value)
    except ValueError as error:
        raise LoopValidationError(
            field_name="offset",
            message="must be a non-negative integer",
        ) from error
