"""Deterministic JSON persistence helpers shared by SQLite mappings."""

from __future__ import annotations

import json
from typing import cast

from src.app.models.changelog import JsonObject


def serialize_json(value: object | None) -> str | None:
    """Serialize optional JSON-compatible data deterministically."""

    if value is None:
        return None
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def deserialize_json_object(value: str | None) -> JsonObject | None:
    """Deserialize an optional stored JSON object."""

    if value is None:
        return None
    return cast(JsonObject, json.loads(value))
