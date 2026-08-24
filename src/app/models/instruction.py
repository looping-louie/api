"""Domain models for persisted and workspace-visible instructions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Mapping

from src.app.catalogs.persona_skills import InstructionOrigin


InstructionType = Literal['persona', 'skill']


@dataclass(frozen=True, slots=True)
class InstructionSummary:
    """Lightweight persisted instruction representation."""

    id: str
    name: str
    description: str
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class InstructionDocument:
    """Complete workspace-owned persona or skill document."""

    id: str
    workspace_id: str
    instruction_type: InstructionType
    name: str
    description: str
    instructions: str
    metadata: Mapping[str, object]
    version: int
    created_at: datetime
    updated_at: datetime
    source_instruction_id: str | None = None


@dataclass(frozen=True, slots=True)
class AvailableInstructionSummary:
    """Instruction summary in a workspace's effective library."""

    id: str
    workspace_id: str
    instruction_type: InstructionType
    origin: InstructionOrigin
    owner_workspace_id: str | None
    source_instruction_id: str | None
    name: str
    description: str
    enabled: bool
    enabled_by_default: bool
    deprecated: bool
    catalog_version: int | None
    version: int
    created_at: datetime
    updated_at: datetime

    @property
    def selectable(self) -> bool:
        """Return whether new compositions may select this definition."""

        return self.enabled and not self.deprecated

    @property
    def editable(self) -> bool:
        """Return whether the workspace may mutate this definition."""

        return (
            self.origin == InstructionOrigin.CUSTOM
            and self.owner_workspace_id == self.workspace_id
        )

    @property
    def duplicable(self) -> bool:
        """Return whether the workspace may fork this definition."""

        return not self.deprecated


@dataclass(frozen=True, slots=True)
class AvailableInstructionDocument:
    """Complete instruction in a workspace's effective library."""

    id: str
    workspace_id: str
    instruction_type: InstructionType
    origin: InstructionOrigin
    owner_workspace_id: str | None
    source_instruction_id: str | None
    name: str
    description: str
    instructions: str
    metadata: Mapping[str, object]
    enabled: bool
    enabled_by_default: bool
    deprecated: bool
    catalog_version: int | None
    checksum: str | None
    version: int
    created_at: datetime
    updated_at: datetime

    @property
    def selectable(self) -> bool:
        """Return whether new compositions may select this definition."""

        return self.enabled and not self.deprecated

    @property
    def editable(self) -> bool:
        """Return whether the workspace may mutate this definition."""

        return (
            self.origin == InstructionOrigin.CUSTOM
            and self.owner_workspace_id == self.workspace_id
        )

    @property
    def duplicable(self) -> bool:
        """Return whether the workspace may fork this definition."""

        return not self.deprecated
