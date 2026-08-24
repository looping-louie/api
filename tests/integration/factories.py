"""Factories shared by SQLite integration tests."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from src.app.services.persona_skills import (
    InstructionDocument,
    InstructionType,
)


DEFAULT_DATETIME = datetime(
    2026,
    7,
    13,
    10,
    0,
    tzinfo=UTC,
)


def build_instruction(
    *,
    instruction_id: str = "instruction-1",
    workspace_id: str = "workspace-1",
    instruction_type: InstructionType = "persona",
    name: str = "Security Reviewer",
    description: str = "Reviews security concerns.",
    instructions: str = "Review the supplied work for security issues.",
    metadata: Mapping[str, Any] | None = None,
    version: int = 1,
    created_at: datetime = DEFAULT_DATETIME,
    updated_at: datetime = DEFAULT_DATETIME,
) -> InstructionDocument:
    """Build one instruction document."""

    return InstructionDocument(
        id=instruction_id,
        workspace_id=workspace_id,
        instruction_type=instruction_type,
        name=name,
        description=description,
        instructions=instructions,
        metadata=dict(metadata or {}),
        version=version,
        created_at=created_at,
        updated_at=updated_at,
    )
