from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Callable, Literal, Mapping, Protocol, Sequence
from uuid import uuid4

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
        """Return lightweight instruction records."""
        ...

    async def get(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> InstructionDocument | None:
        """Return one complete instruction document."""
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
    ) -> list[InstructionSummary]:
        """List personas or skills without returning their full instructions."""

        self._require_instruction_type(instruction_type)

        summaries = await self._repository.list_summaries(
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
    ) -> InstructionDocument:
        """Return a complete persona or skill document."""

        self._require_instruction_type(instruction_type)

        document = await self._require_document(
            workspace_id=self._require_text(workspace_id, "workspace_id"),
            instruction_type=instruction_type,
            instruction_id=self._require_text(instruction_id, "instruction_id"),
        )

        return self._copy_document(document)

    async def create(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        payload: InstructionCreate,
    ) -> InstructionDocument:
        """Create a persona or skill."""

        self._require_instruction_type(instruction_type)
        workspace_id = self._require_text(workspace_id, "workspace_id")
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
        )

        created = await self._repository.create(document=document)
        return self._copy_document(created)

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

        current = await self._require_document(
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

        await self._require_document(
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

    async def _require_document(
        self,
        *,
        workspace_id: str,
        instruction_type: InstructionType,
        instruction_id: str,
    ) -> InstructionDocument:
        document = await self._repository.get(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )

        if document is None:
            raise InstructionNotFoundError(
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
        current = await self._repository.get(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )

        if current is None:
            raise InstructionNotFoundError(
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
    def _default_id_factory() -> str:
        return str(uuid4())

    @staticmethod
    def _default_clock() -> datetime:
        return datetime.now(UTC)
