"""Shared construction and diff helpers for resource changelogs."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from src.app.models.changelog import ChangelogMetadata, JsonObject


def build_changelog_metadata(
    *,
    entry_id: str,
    workspace_id: str,
    actor_id: str,
    changed_at: datetime,
    diff: JsonObject | None = None,
    content: JsonObject | None = None,
) -> ChangelogMetadata:
    """Build generated changelog values independently of resource identity."""

    return ChangelogMetadata(
        id=entry_id,
        workspace_id=workspace_id,
        actor_id=actor_id,
        changed_at=changed_at,
        diff=diff,
        content=content,
    )


def changed_field_diff(
    before: Mapping[str, object],
    after: Mapping[str, object],
    fields: frozenset[str],
) -> JsonObject:
    """Return effective JSON-compatible changes for supplied fields."""

    return {
        field: {"from": before[field], "to": after[field]}
        for field in fields
        if before[field] != after[field]
    }
