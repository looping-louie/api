from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Callable, Literal, Mapping, Protocol, Sequence
from uuid import uuid4

from src.app.catalogs.instructions import InstructionOrigin

from .dependency_checker import DependencyChecker
from .reference_resolver import ResourceReference
from .validation_service import ValidationService


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


@dataclass(frozen=True, slots=True)
class InstructionCreate:
    """Data required to create a persona or skill."""

    name: str
    description: str
    instructions: str
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class InstructionUpdate:
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
    ) -> Sequence[AvailableInstructionSummary]:
        """Return the effective instruction library for a workspace."""
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
        """
        Persist an instruction update atomically.

        The implementation must only update the record when its current
        version matches expected_version. It returns None when the update
        cannot be applied.
        """
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


class InstructionService:
    """Shared application service for personas and skills."""

    def __init__(
        self,
        *,
        repository: InstructionRepository,
        validation_service: ValidationService,
        dependency_checker: DependencyChecker,
        id_factory: IdFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._repository = repository
        self._validation_service = validation_service
        self._dependency_checker = dependency_checker
        self._id_factory = id_factory or self._default_id_factory
        self._clock = clock or self._default_clock

    async def list(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        search: str | None = None,
    ) -> list[AvailableInstructionSummary]:
        """List the effective instruction library of a workspace."""

        self._require_instruction_type(instruction_type)

        summaries = await self._repository.list_available_for_workspace(
            workspace_id=self._require_text(workspace_id, "workspace_id"),
            instruction_type=instruction_type,
            search=self._normalize_search(search),
        )

        return list(summaries)

    async def describe(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
        include_deprecated: bool = False,
    ) -> AvailableInstructionDocument:
        """Return a visible instruction, including disabled definitions."""

        self._require_instruction_type(instruction_type)

        document = await self._require_available(
            workspace_id=self._require_text(workspace_id, "workspace_id"),
            instruction_type=instruction_type,
            instruction_id=self._require_text(instruction_id, "instruction_id"),
            include_deprecated=include_deprecated,
        )

        return self._copy_available_document(document)

    async def create(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        payload: InstructionCreate,
    ) -> InstructionDocument:
        """Create a workspace-owned custom instruction."""

        self._require_instruction_type(instruction_type)
        workspace_id = self._require_text(workspace_id, "workspace_id")
        return await self._create_custom(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            payload=payload,
            source_instruction_id=None,
        )

    async def enable(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> AvailableInstructionDocument:
        """Enable a visible instruction for new compositions."""

        return await self._set_enabled(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
            enabled=True,
        )

    async def disable(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> AvailableInstructionDocument:
        """Disable a visible instruction without hiding its definition."""

        return await self._set_enabled(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
            enabled=False,
        )

    async def duplicate(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
        name: str | None = None,
    ) -> InstructionDocument:
        """Fork a visible instruction into a new editable custom copy."""

        self._require_instruction_type(instruction_type)
        workspace_id = self._require_text(
            workspace_id,
            "workspace_id",
        )
        instruction_id = self._require_text(
            instruction_id,
            "instruction_id",
        )
        source = await self._require_available(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
            include_deprecated=False,
        )
        duplicate_name = (
            self._require_text(name, "name")
            if name is not None
            else f"{source.name} Copy"
        )

        return await self._create_custom(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            payload=InstructionCreate(
                name=duplicate_name,
                description=source.description,
                instructions=source.instructions,
                metadata=deepcopy(dict(source.metadata)),
            ),
            source_instruction_id=source.id,
        )

    async def resolve_for_selection(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> AvailableInstructionDocument:
        """Resolve an instruction that may be used in new compositions."""

        document = await self.describe(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
            include_deprecated=True,
        )

        if not document.selectable:
            raise InstructionDisabledError(
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

        return document

    async def update(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
        payload: InstructionUpdate,
    ) -> InstructionDocument:
        """Update a persona or skill using optimistic concurrency."""

        self._require_instruction_type(instruction_type)
        workspace_id = self._require_text(workspace_id, "workspace_id")
        instruction_id = self._require_text(instruction_id, "instruction_id")

        current = await self._require_owned_custom(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )

        self._validation_service.require_expected_version(
            expected_version=payload.expected_version,
            current_version=current.version,
        )

        normalized = self._normalize_update(payload)

        if normalized.name is not None:
            await self._validation_service.require_unique_name(
                workspace_id=workspace_id,
                resource_type=instruction_type,
                name=normalized.name,
                exclude_resource_id=instruction_id,
            )

        updated = replace(
            current,
            name=normalized.name if normalized.name is not None else current.name,
            description=(
                normalized.description
                if normalized.description is not None
                else current.description
            ),
            instructions=(
                normalized.instructions
                if normalized.instructions is not None
                else current.instructions
            ),
            metadata=(
                deepcopy(dict(normalized.metadata))
                if normalized.metadata is not None
                else deepcopy(dict(current.metadata))
            ),
            version=current.version + 1,
            updated_at=self._clock(),
        )

        persisted = await self._repository.update(
            document=updated,
            expected_version=payload.expected_version,
        )

        if persisted is None:
            await self._raise_update_conflict(
                workspace_id=workspace_id,
                instruction_type=instruction_type,
                instruction_id=instruction_id,
                expected_version=payload.expected_version,
            )

        return self._copy_document(persisted)

    async def delete(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> None:
        """Delete a persona or skill after checking its dependencies."""

        self._require_instruction_type(instruction_type)
        workspace_id = self._require_text(workspace_id, "workspace_id")
        instruction_id = self._require_text(instruction_id, "instruction_id")

        await self._require_owned_custom(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )

        await self._dependency_checker.require_deletable(
            workspace_id=workspace_id,
            target=ResourceReference(
                resource_type=instruction_type,
                resource_id=instruction_id,
            ),
        )

        deleted = await self._repository.delete(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )

        if not deleted:
            raise InstructionNotFoundError(
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

    async def _create_custom(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        payload: InstructionCreate,
        source_instruction_id: str | None,
    ) -> InstructionDocument:
        normalized = self._normalize_create(payload)

        await self._validation_service.require_unique_name(
            workspace_id=workspace_id,
            resource_type=instruction_type,
            name=normalized.name,
        )

        now = self._clock()
        document = InstructionDocument(
            id=self._id_factory(),
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            name=normalized.name,
            description=normalized.description,
            instructions=normalized.instructions,
            metadata=deepcopy(dict(normalized.metadata)),
            version=1,
            created_at=now,
            updated_at=now,
            source_instruction_id=source_instruction_id,
        )
        created = await self._repository.create(
            document=document,
        )
        return self._copy_document(created)

    async def _set_enabled(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
        enabled: bool,
    ) -> AvailableInstructionDocument:
        self._require_instruction_type(instruction_type)
        workspace_id = self._require_text(
            workspace_id,
            "workspace_id",
        )
        instruction_id = self._require_text(
            instruction_id,
            "instruction_id",
        )
        current = await self._require_available(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
            include_deprecated=True,
        )

        if current.deprecated:
            raise InstructionDisabledError(
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

        persisted = await self._repository.set_enabled(
            workspace_id=workspace_id,
            instruction_id=instruction_id,
            enabled=enabled,
        )

        if not persisted:
            raise InstructionNotFoundError(
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

        return await self._require_available(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
            include_deprecated=False,
        )

    async def _require_available(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
        include_deprecated: bool,
    ) -> AvailableInstructionDocument:
        document = await self._repository.get_available_for_workspace(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
            include_deprecated=include_deprecated,
        )

        if document is None:
            raise InstructionNotFoundError(
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

        return document

    async def _require_owned_custom(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> InstructionDocument:
        available = await self._repository.get_available_for_workspace(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
            include_deprecated=True,
        )

        if (
            available is not None
            and available.origin == InstructionOrigin.BUILTIN
        ):
            raise BuiltinInstructionImmutableError(
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

        document = await self._repository.get_owned_custom(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )

        if document is None:
            raise InstructionNotOwnedError(
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

        return document

    async def _raise_update_conflict(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
        expected_version: int,
    ) -> None:
        current = await self._repository.get_owned_custom(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )

        if current is None:
            raise InstructionNotOwnedError(
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

        raise InstructionVersionConflictError(
            instruction_type=instruction_type,
            instruction_id=instruction_id,
            expected_version=expected_version,
            current_version=current.version,
        )

    def _normalize_create(self, payload: InstructionCreate) -> InstructionCreate:
        return InstructionCreate(
            name=self._require_text(payload.name, "name"),
            description=self._normalize_description(payload.description),
            instructions=self._require_text(payload.instructions, "instructions"),
            metadata=deepcopy(dict(payload.metadata)),
        )

    def _normalize_update(self, payload: InstructionUpdate) -> InstructionUpdate:
        if payload.expected_version < 1:
            raise InstructionValidationError(
                field_name="expected_version",
                message="must be greater than zero",
            )

        return InstructionUpdate(
            expected_version=payload.expected_version,
            name=(
                self._require_text(payload.name, "name")
                if payload.name is not None
                else None
            ),
            description=(
                self._normalize_description(payload.description)
                if payload.description is not None
                else None
            ),
            instructions=(
                self._require_text(payload.instructions, "instructions")
                if payload.instructions is not None
                else None
            ),
            metadata=(
                deepcopy(dict(payload.metadata))
                if payload.metadata is not None
                else None
            ),
        )

    @staticmethod
    def _require_instruction_type(instruction_type: str) -> None:
        if instruction_type not in SUPPORTED_INSTRUCTION_TYPES:
            raise InvalidInstructionTypeError(instruction_type)

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise InstructionValidationError(
                field_name=field_name,
                message="must not be empty",
            )

        return normalized

    @staticmethod
    def _normalize_description(value: str) -> str:
        return value.strip()

    @staticmethod
    def _normalize_search(search: str | None) -> str | None:
        if search is None:
            return None

        normalized = search.strip()
        return normalized or None

    @staticmethod
    def _copy_document(document: InstructionDocument) -> InstructionDocument:
        return replace(
            document,
            metadata=deepcopy(dict(document.metadata)),
        )

    @staticmethod
    def _copy_available_document(
        document: AvailableInstructionDocument,
    ) -> AvailableInstructionDocument:
        return replace(
            document,
            metadata=deepcopy(dict(document.metadata)),
        )

    @staticmethod
    def _default_id_factory() -> str:
        return str(uuid4())

    @staticmethod
    def _default_clock() -> datetime:
        return datetime.now(UTC)
