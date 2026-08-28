"""Row mapping and value normalization for instruction persistence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any, cast

import aiosqlite

from src.app.catalogs.persona_skills import InstructionOrigin
from src.app.services.persona_skills import (
    AvailableDefinitionDocument,
    AvailableDefinitionSummary,
    DefinitionDocument,
    DefinitionSummary,
    DefinitionType,
)


def to_summary(row: aiosqlite.Row) -> DefinitionSummary:
    """Convert a SQLite row into an editable instruction summary."""

    return DefinitionSummary(
        id=str(row["id"]),
        name=str(row["name"]),
        description=str(row["description"]),
        version=int(row["version"]),
        created_at=parse_datetime(row["created_at"]),
        updated_at=parse_datetime(row["updated_at"]),
    )


def to_document(row: aiosqlite.Row) -> DefinitionDocument:
    """Convert a SQLite row into an editable instruction document."""

    return DefinitionDocument(
        id=str(row["id"]),
        project_id=str(row["project_id"]),
        instruction_type=cast(
            DefinitionType,
            str(row["instruction_type"]),
        ),
        source_instruction_id=(
            str(row["source_instruction_id"])
            if row["source_instruction_id"] is not None
            else None
        ),
        name=str(row["name"]),
        description=str(row["description"]),
        instructions=str(row["content"]),
        metadata=parse_metadata(row["metadata_json"]),
        version=int(row["version"]),
        created_at=parse_datetime(row["created_at"]),
        updated_at=parse_datetime(row["updated_at"]),
    )


def to_available_summary(
    row: aiosqlite.Row,
    *,
    project_id: str,
) -> AvailableDefinitionSummary:
    """Convert a row into a workspace-scoped available summary."""

    return AvailableDefinitionSummary(
        id=str(row["id"]),
        project_id=project_id,
        instruction_type=cast(
            DefinitionType,
            str(row["instruction_type"]),
        ),
        origin=InstructionOrigin(str(row["origin"])),
        owner_project_id=(
            str(row["owner_project_id"])
            if row["owner_project_id"] is not None
            else None
        ),
        source_instruction_id=(
            str(row["source_instruction_id"])
            if row["source_instruction_id"] is not None
            else None
        ),
        name=str(row["name"]),
        description=str(row["description"]),
        enabled=bool(row["enabled"]),
        enabled_by_default=bool(row["enabled_by_default"]),
        deprecated=bool(row["deprecated"]),
        catalog_version=(
            int(row["catalog_version"])
            if row["catalog_version"] is not None
            else None
        ),
        version=int(row["version"]),
        created_at=parse_datetime(row["created_at"]),
        updated_at=parse_datetime(row["updated_at"]),
        category=(
            str(row["category"])
            if row["category"] is not None
            else None
        ),
    )


def to_available_document(
    row: aiosqlite.Row,
    *,
    project_id: str,
) -> AvailableDefinitionDocument:
    """Convert a row into a workspace-scoped available document."""

    return AvailableDefinitionDocument(
        id=str(row["id"]),
        project_id=project_id,
        instruction_type=cast(
            DefinitionType,
            str(row["instruction_type"]),
        ),
        origin=InstructionOrigin(str(row["origin"])),
        owner_project_id=(
            str(row["owner_project_id"])
            if row["owner_project_id"] is not None
            else None
        ),
        source_instruction_id=(
            str(row["source_instruction_id"])
            if row["source_instruction_id"] is not None
            else None
        ),
        name=str(row["name"]),
        description=str(row["description"]),
        instructions=str(row["content"]),
        metadata=parse_metadata(row["metadata_json"]),
        enabled=bool(row["enabled"]),
        enabled_by_default=bool(row["enabled_by_default"]),
        deprecated=bool(row["deprecated"]),
        catalog_version=(
            int(row["catalog_version"])
            if row["catalog_version"] is not None
            else None
        ),
        checksum=(
            str(row["checksum"])
            if row["checksum"] is not None
            else None
        ),
        version=int(row["version"]),
        created_at=parse_datetime(row["created_at"]),
        updated_at=parse_datetime(row["updated_at"]),
    )


def normalize_name(name: str) -> str:
    """Normalize a display name for storage and comparison."""

    return " ".join(name.strip().casefold().split())


def normalize_search(search: str | None) -> str | None:
    """Normalize optional search text and discard empty values."""

    if search is None:
        return None

    normalized = normalize_name(search)
    return normalized or None


def escape_like(value: str) -> str:
    """Escape SQLite LIKE wildcard characters in literal search text."""

    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def serialize_metadata(metadata: Mapping[str, Any]) -> str:
    """Serialize instruction metadata deterministically for SQLite."""

    return json.dumps(
        dict(metadata),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def parse_metadata(raw_metadata: object) -> dict[str, Any]:
    """Parse stored instruction metadata and require a JSON object."""

    parsed = json.loads(str(raw_metadata))

    if not isinstance(parsed, dict):
        raise ValueError(
            "Stored instruction metadata must be a JSON object."
        )

    return parsed


def serialize_datetime(value: datetime) -> str:
    """Serialize a datetime using its ISO 8601 representation."""

    return value.isoformat()


def parse_datetime(value: object) -> datetime:
    """Parse an ISO 8601 datetime, including the UTC Z suffix."""

    serialized = str(value)

    if serialized.endswith("Z"):
        serialized = f"{serialized[:-1]}+00:00"

    return datetime.fromisoformat(serialized)
