from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Literal, Protocol
from uuid import uuid4

from .dependency_checker import DependencyChecker
from .reference_resolver import ResourceReference
from .validation_service import ValidationService


CompositionType = Literal["council", "loop"]
IdFactory = Callable[[], str]
Clock = Callable[[], datetime]

SUPPORTED_COMPOSITION_TYPES: frozenset[str] = frozenset(
    {
        "council",
        "loop",
    }
)


@dataclass(frozen=True, slots=True)
class CompositionSummary:
    """Lightweight council or loop representation used by list endpoints."""

    id: str
    name: str
    description: str
    version: int
    item_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class CompositionDocument:
    """Complete council or loop aggregate."""

    id: str
    workspace_id: str
    composition_type: CompositionType
    name: str
    description: str
    attributes: Mapping[str, object]
    items: Sequence[Mapping[str, object]]
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class CompositionCreate:
    """Root values and child items required to create an aggregate."""

    name: str
    description: str
    attributes: Mapping[str, object] = field(default_factory=dict)
    items: Sequence[Mapping[str, object]] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class CompositionUpdate:
    """Partial changes applied to an existing aggregate."""

    expected_version: int
    name: str | None = None
    description: str | None = None
    attributes: Mapping[str, object] | None = None
    items: Sequence[Mapping[str, object]] | None = None


class CompositionRepository(Protocol):
    """Persistence contract required by CompositionService."""

    async def list_summaries(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        search: str | None = None,
    ) -> Sequence[CompositionSummary]:
        """Return lightweight aggregate records."""
        ...

    async def get(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        composition_id: str,
    ) -> CompositionDocument | None:
        """Return one complete aggregate."""
        ...

    async def create(
        self,
        *,
        document: CompositionDocument,
    ) -> CompositionDocument:
        """
        Persist the aggregate root and all child items atomically.

        The returned document must represent the persisted state.
        """
        ...

    async def update(
        self,
        *,
        document: CompositionDocument,
        expected_version: int,
    ) -> CompositionDocument | None:
        """
        Update the aggregate root and child items atomically.

        The implementation must only update the record when its current
        version matches expected_version. It returns None when the update
        cannot be applied.
        """
        ...

    async def delete(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        composition_id: str,
    ) -> bool:
        """
        Delete the aggregate root and child items atomically.

        Return whether the aggregate existed.
        """
        ...


class CompositionServiceError(Exception):
    """Base error raised by CompositionService."""


class InvalidCompositionTypeError(CompositionServiceError):
    """Raised when an unsupported composition type is requested."""

    def __init__(self, composition_type: str) -> None:
        super().__init__(f"Unsupported composition type: {composition_type}")
        self.composition_type = composition_type


class CompositionNotFoundError(CompositionServiceError):
    """Raised when a composition cannot be found."""

    def __init__(
        self,
        *,
        composition_type: CompositionType,
        composition_id: str,
    ) -> None:
        message = (
            f"{composition_type.capitalize()} '{composition_id}' was not found."
        )
        super().__init__(message)
        self.composition_type = composition_type
        self.composition_id = composition_id


class CompositionVersionConflictError(CompositionServiceError):
    """Raised when an update loses an optimistic concurrency race."""

    def __init__(
        self,
        *,
        composition_type: CompositionType,
        composition_id: str,
        expected_version: int,
        current_version: int,
    ) -> None:
        message = (
            f"{composition_type.capitalize()} '{composition_id}' has version "
            f"{current_version}; expected version {expected_version}."
        )
        super().__init__(message)
        self.composition_type = composition_type
        self.composition_id = composition_id
        self.expected_version = expected_version
        self.current_version = current_version


class CompositionValidationError(CompositionServiceError):
    """Raised when composition data is invalid."""

    def __init__(self, *, field_name: str, message: str) -> None:
        super().__init__(f"Invalid '{field_name}': {message}")
        self.field_name = field_name
        self.message = message


class CompositionService:
    """Shared application service for councils and loops."""

    def __init__(
        self,
        *,
        repository: CompositionRepository,
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
        composition_type: CompositionType,
        search: str | None = None,
    ) -> list[CompositionSummary]:
        """List councils or loops without expanding their child items."""

        self._require_composition_type(composition_type)

        summaries = await self._repository.list_summaries(
            workspace_id=self._require_text(
                workspace_id,
                "workspace_id",
            ),
            composition_type=composition_type,
            search=self._normalize_search(search),
        )

        return list(summaries)

    async def describe(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        composition_id: str,
    ) -> CompositionDocument:
        """Return a complete council or loop aggregate."""

        self._require_composition_type(composition_type)

        document = await self._require_document(
            workspace_id=self._require_text(
                workspace_id,
                "workspace_id",
            ),
            composition_type=composition_type,
            composition_id=self._require_text(
                composition_id,
                "composition_id",
            ),
        )

        return self._copy_document(document)

    async def create(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        payload: CompositionCreate,
    ) -> CompositionDocument:
        """Create a council or loop atomically."""

        self._require_composition_type(composition_type)
        workspace_id = self._require_text(
            workspace_id,
            "workspace_id",
        )
        normalized = self._normalize_create(payload)

        await self._validation_service.require_unique_name(
            workspace_id=workspace_id,
            resource_type=composition_type,
            name=normalized.name,
        )

        now = self._clock()
        document = CompositionDocument(
            id=self._id_factory(),
            workspace_id=workspace_id,
            composition_type=composition_type,
            name=normalized.name,
            description=normalized.description,
            attributes=deepcopy(dict(normalized.attributes)),
            items=self._copy_items(normalized.items),
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
        composition_type: CompositionType,
        composition_id: str,
        payload: CompositionUpdate,
    ) -> CompositionDocument:
        """Update an aggregate using optimistic concurrency."""

        self._require_composition_type(composition_type)
        workspace_id = self._require_text(
            workspace_id,
            "workspace_id",
        )
        composition_id = self._require_text(
            composition_id,
            "composition_id",
        )

        current = await self._require_document(
            workspace_id=workspace_id,
            composition_type=composition_type,
            composition_id=composition_id,
        )

        self._validation_service.require_expected_version(
            expected_version=payload.expected_version,
            current_version=current.version,
        )

        normalized = self._normalize_update(payload)

        if normalized.name is not None:
            await self._validation_service.require_unique_name(
                workspace_id=workspace_id,
                resource_type=composition_type,
                name=normalized.name,
                exclude_resource_id=composition_id,
            )

        updated = replace(
            current,
            name=(
                normalized.name
                if normalized.name is not None
                else current.name
            ),
            description=(
                normalized.description
                if normalized.description is not None
                else current.description
            ),
            attributes=(
                deepcopy(dict(normalized.attributes))
                if normalized.attributes is not None
                else deepcopy(dict(current.attributes))
            ),
            items=(
                self._copy_items(normalized.items)
                if normalized.items is not None
                else self._copy_items(current.items)
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
                composition_type=composition_type,
                composition_id=composition_id,
                expected_version=payload.expected_version,
            )

        return self._copy_document(persisted)

    async def delete(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        composition_id: str,
    ) -> None:
        """Delete an aggregate after checking its dependencies."""

        self._require_composition_type(composition_type)
        workspace_id = self._require_text(
            workspace_id,
            "workspace_id",
        )
        composition_id = self._require_text(
            composition_id,
            "composition_id",
        )

        await self._require_document(
            workspace_id=workspace_id,
            composition_type=composition_type,
            composition_id=composition_id,
        )

        await self._dependency_checker.require_deletable(
            workspace_id=workspace_id,
            target=ResourceReference(
                resource_type=composition_type,
                resource_id=composition_id,
            ),
        )

        deleted = await self._repository.delete(
            workspace_id=workspace_id,
            composition_type=composition_type,
            composition_id=composition_id,
        )

        if not deleted:
            raise CompositionNotFoundError(
                composition_type=composition_type,
                composition_id=composition_id,
            )

    async def _require_document(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        composition_id: str,
    ) -> CompositionDocument:
        document = await self._repository.get(
            workspace_id=workspace_id,
            composition_type=composition_type,
            composition_id=composition_id,
        )

        if document is None:
            raise CompositionNotFoundError(
                composition_type=composition_type,
                composition_id=composition_id,
            )

        return document

    async def _raise_update_conflict(
        self,
        *,
        workspace_id: str,
        composition_type: CompositionType,
        composition_id: str,
        expected_version: int,
    ) -> None:
        current = await self._repository.get(
            workspace_id=workspace_id,
            composition_type=composition_type,
            composition_id=composition_id,
        )

        if current is None:
            raise CompositionNotFoundError(
                composition_type=composition_type,
                composition_id=composition_id,
            )

        raise CompositionVersionConflictError(
            composition_type=composition_type,
            composition_id=composition_id,
            expected_version=expected_version,
            current_version=current.version,
        )

    def _normalize_create(
        self,
        payload: CompositionCreate,
    ) -> CompositionCreate:
        if not isinstance(payload, CompositionCreate):
            raise CompositionValidationError(
                field_name="payload",
                message="must be a CompositionCreate",
            )

        return CompositionCreate(
            name=self._require_text(payload.name, "name"),
            description=self._normalize_description(
                payload.description,
            ),
            attributes=self._normalize_mapping(
                payload.attributes,
                "attributes",
            ),
            items=self._normalize_items(payload.items),
        )

    def _normalize_update(
        self,
        payload: CompositionUpdate,
    ) -> CompositionUpdate:
        if not isinstance(payload, CompositionUpdate):
            raise CompositionValidationError(
                field_name="payload",
                message="must be a CompositionUpdate",
            )

        self._require_positive_integer(
            payload.expected_version,
            "expected_version",
        )

        return CompositionUpdate(
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
            attributes=(
                self._normalize_mapping(
                    payload.attributes,
                    "attributes",
                )
                if payload.attributes is not None
                else None
            ),
            items=(
                self._normalize_items(payload.items)
                if payload.items is not None
                else None
            ),
        )

    def _normalize_items(
        self,
        items: Sequence[Mapping[str, object]],
    ) -> tuple[dict[str, object], ...]:
        if not self._is_sequence(items):
            raise CompositionValidationError(
                field_name="items",
                message="must be a sequence of objects",
            )

        return tuple(
            self._normalize_mapping(
                item,
                f"items[{index}]",
            )
            for index, item in enumerate(items)
        )

    def _normalize_mapping(
        self,
        value: Mapping[str, object],
        field_name: str,
    ) -> dict[str, object]:
        if not isinstance(value, Mapping):
            raise CompositionValidationError(
                field_name=field_name,
                message="must be an object",
            )

        normalized: dict[str, object] = {}

        for key, item in value.items():
            normalized_key = self._require_text(
                key,
                f"{field_name}.key",
            )

            if normalized_key in normalized:
                raise CompositionValidationError(
                    field_name=field_name,
                    message=(
                        f"contains duplicate normalized key "
                        f"'{normalized_key}'"
                    ),
                )

            normalized[normalized_key] = deepcopy(item)

        return normalized

    @staticmethod
    def _copy_document(
        document: CompositionDocument,
    ) -> CompositionDocument:
        return replace(
            document,
            attributes=deepcopy(dict(document.attributes)),
            items=CompositionService._copy_items(document.items),
        )

    @staticmethod
    def _copy_items(
        items: Sequence[Mapping[str, object]],
    ) -> tuple[dict[str, object], ...]:
        return tuple(
            deepcopy(dict(item))
            for item in items
        )

    @staticmethod
    def _require_composition_type(composition_type: str) -> None:
        if composition_type not in SUPPORTED_COMPOSITION_TYPES:
            raise InvalidCompositionTypeError(composition_type)

    @staticmethod
    def _normalize_description(value: str) -> str:
        if not isinstance(value, str):
            raise CompositionValidationError(
                field_name="description",
                message="must be a string",
            )

        return value.strip()

    @staticmethod
    def _normalize_search(search: str | None) -> str | None:
        if search is None:
            return None

        if not isinstance(search, str):
            raise CompositionValidationError(
                field_name="search",
                message="must be a string",
            )

        normalized = search.strip()
        return normalized or None

    @staticmethod
    def _require_positive_integer(
        value: int,
        field_name: str,
    ) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise CompositionValidationError(
                field_name=field_name,
                message="must be an integer greater than zero",
            )

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        if not isinstance(value, str):
            raise CompositionValidationError(
                field_name=field_name,
                message="must be a string",
            )

        normalized = value.strip()

        if not normalized:
            raise CompositionValidationError(
                field_name=field_name,
                message="must not be empty",
            )

        return normalized

    @staticmethod
    def _is_sequence(value: object) -> bool:
        return isinstance(value, Sequence) and not isinstance(
            value,
            (str, bytes, bytearray),
        )

    @staticmethod
    def _default_id_factory() -> str:
        return str(uuid4())

    @staticmethod
    def _default_clock() -> datetime:
        return datetime.now(UTC)
