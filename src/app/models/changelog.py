"""Shared values stored by immutable resource changelogs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


JsonObject = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ChangelogMetadata:
    """Generated fields shared by every changelog entry."""

    id: str
    project_id: str
    actor_id: str
    changed_at: datetime
    diff: JsonObject | None
    content: JsonObject | None
