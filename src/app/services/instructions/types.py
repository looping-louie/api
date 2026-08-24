"""Instruction domain contracts and errors."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Callable, Literal, Mapping, Protocol, Sequence
from uuid import uuid4

from src.app.catalogs.persona_skills import (
    CatalogInstructionCategory,
    CatalogInstructionSort,
    CatalogInstructionStatus,
    InstructionOrigin,
)


InstructionType = Literal["persona", "skill"]
IdFactory = Callable[[], str]
Clock = Callable[[], datetime]

SUPPORTED_INSTRUCTION_TYPES: frozenset[str] = frozenset(
    {
        "persona",
        "skill",
    }
)


@dataclass(frozen=True, slots=True)
class InstructionSummary:
    """Lightweight instruction representation used by list endpoints."""

    id: str
    name: str
    description: str
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class InstructionDocument:
    """Complete persona or skill document."""

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
    """Instruction visible in one workspace's effective library."""

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
    category: str | None = None

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
class AvailableInstructionPage(Sequence[AvailableInstructionSummary]):
    """One filtered page of a workspace's effective instruction catalog."""

    items: tuple[AvailableInstructionSummary, ...]
    total: int

    def __len__(self) -> int:
        """Return the number of summaries in this page."""

        return len(self.items)

    def __getitem__(
        self,
        index: int | slice,
    ) -> AvailableInstructionSummary | tuple[AvailableInstructionSummary, ...]:
        """Return one summary or a slice from the current page."""

        return self.items[index]


@dataclass(frozen=True, slots=True)
class AvailableInstructionDocument:
    """Complete instruction resolved in one workspace's library."""

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


@dataclass(frozen=True, slots=True)
class DefinitionCreate:
    """Data required to create a persona or skill."""

    name: str
    description: str
    instructions: str
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DefinitionUpdate:
    """Partial changes applied to a persona or skill."""

    expected_version: int
    name: str | None = None
    description: str | None = None
    instructions: str | None = None
    metadata: Mapping[str, object] | None = None


class InstructionRepository(Protocol):
    """Persistence contract required by InstructionService."""

    async def list_summaries(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        search: str | None = None,
    ) -> Sequence[InstructionSummary]:
        """Return owned custom summaries for editing workflows."""
        ...

    async def get(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> InstructionDocument | None:
        """Return one custom instruction owned by the workspace."""
        ...

    async def list_available_for_workspace(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        search: str | None = None,
        include_deprecated: bool = False,
        status: CatalogInstructionStatus | None = None,
        categories: Sequence[CatalogInstructionCategory] = (),
        sort: CatalogInstructionSort | None = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> AvailableInstructionPage:
        """Return a filtered page of the workspace instruction catalog."""
        ...

    async def get_available_for_workspace(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
        include_deprecated: bool = False,
    ) -> AvailableInstructionDocument | None:
        """Resolve a visible instruction, including disabled definitions."""
        ...

    async def get_owned_custom(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> InstructionDocument | None:
        """Return a custom instruction owned by the workspace."""
        ...

    async def set_enabled(
        self,
        *,
        workspace_id: str,
        instruction_id: str,
        enabled: bool,
    ) -> bool:
        """Persist an explicit workspace enablement override."""
        ...

    async def is_enabled(
        self,
        *,
        workspace_id: str,
        instruction_id: str,
    ) -> bool:
        """Return whether an instruction is selectable in the workspace."""
        ...

    async def create(
        self,
        *,
        document: InstructionDocument,
    ) -> InstructionDocument:
        """Persist and return a new instruction document."""
        ...

    async def update(
        self,
        *,
        document: InstructionDocument,
        expected_version: int,
    ) -> InstructionDocument | None:
        """Persist an instruction update atomically."""
        ...

    async def delete(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> bool:
        """Delete an instruction and report whether it existed."""
        ...


class InstructionServiceError(Exception):
    """Base error raised by InstructionService."""


class InvalidInstructionTypeError(InstructionServiceError):
    """Raised when an unsupported instruction type is requested."""

    def __init__(self, instruction_type: str) -> None:
        super().__init__(f"Unsupported instruction type: {instruction_type}")
        self.instruction_type = instruction_type


class InstructionNotFoundError(InstructionServiceError):
    """Raised when an instruction cannot be found."""

    def __init__(
        self,
        *,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> None:
        message = f"{instruction_type.capitalize()} '{instruction_id}' was not found."
        super().__init__(message)
        self.instruction_type = instruction_type
        self.instruction_id = instruction_id


class BuiltinInstructionImmutableError(InstructionServiceError):
    """Raised when a builtin is passed to a mutation operation."""

    def __init__(
        self,
        *,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> None:
        super().__init__(
            f"Builtin {instruction_type} '{instruction_id}' is immutable."
        )
        self.instruction_type = instruction_type
        self.instruction_id = instruction_id


class InstructionDisabledError(InstructionServiceError):
    """Raised when an instruction cannot be selected for new work."""

    def __init__(
        self,
        *,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> None:
        super().__init__(
            f"{instruction_type.capitalize()} '{instruction_id}' is "
            "disabled or deprecated."
        )
        self.instruction_type = instruction_type
        self.instruction_id = instruction_id


class InstructionNotOwnedError(InstructionServiceError):
    """Raised when a mutation target is not owned by the workspace."""

    def __init__(
        self,
        *,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> None:
        super().__init__(
            f"{instruction_type.capitalize()} '{instruction_id}' is not "
            "a custom instruction owned by this workspace."
        )
        self.instruction_type = instruction_type
        self.instruction_id = instruction_id


class InstructionVersionConflictError(InstructionServiceError):
    """Raised when an update uses a stale resource version."""

    def __init__(
        self,
        *,
        instruction_type: InstructionType,
        instruction_id: str,
        expected_version: int,
        current_version: int,
    ) -> None:
        message = (
            f"{instruction_type.capitalize()} '{instruction_id}' has version "
            f"{current_version}; expected version {expected_version}."
        )
        super().__init__(message)
        self.instruction_type = instruction_type
        self.instruction_id = instruction_id
        self.expected_version = expected_version
        self.current_version = current_version


class InstructionValidationError(InstructionServiceError):
    """Raised when instruction content is invalid."""

    def __init__(self, *, field_name: str, message: str) -> None:
        super().__init__(f"Invalid '{field_name}': {message}")
        self.field_name = field_name
        self.message = message


def copy_instruction_document(
    document: InstructionDocument,
) -> InstructionDocument:
    """Copy a document without sharing mutable metadata."""

    return replace(
        document,
        metadata=deepcopy(dict(document.metadata)),
    )


def copy_available_instruction_document(
    document: AvailableInstructionDocument,
) -> AvailableInstructionDocument:
    """Copy a visible document without sharing mutable metadata."""

    return replace(
        document,
        metadata=deepcopy(dict(document.metadata)),
    )


def default_clock() -> datetime:
    """Return the current timezone-aware UTC datetime."""

    return datetime.now(UTC)


def default_id_factory() -> str:
    """Create one opaque instruction identifier."""

    return str(uuid4())
