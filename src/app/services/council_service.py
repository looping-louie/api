from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from .shared.composition_service import (
    CompositionCreate,
    CompositionDocument,
    CompositionService,
    CompositionSummary,
    CompositionUpdate,
)
from .shared.reference_resolver import (
    ReferenceResolver,
    ResourceReference,
)
from .shared.tenant_service import TenantService
from .shared.validation_service import ValidationService


@dataclass(frozen=True, slots=True)
class CouncilAssignment:
    """Persona and skills assigned to a role inside a council."""

    role: str
    persona_id: str
    skill_ids: Sequence[str]


@dataclass(frozen=True, slots=True)
class CouncilCreate:
    """Data required to create a council."""

    name: str
    description: str
    assignments: Sequence[CouncilAssignment]


@dataclass(frozen=True, slots=True)
class CouncilUpdate:
    """Partial changes applied to an existing council."""

    expected_version: int
    name: str | None = None
    description: str | None = None
    assignments: Sequence[CouncilAssignment] | None = None


@dataclass(frozen=True, slots=True)
class CouncilDocument:
    """Complete council representation."""

    id: str
    workspace_id: str
    name: str
    description: str
    assignments: tuple[CouncilAssignment, ...]
    version: int
    created_at: datetime
    updated_at: datetime


class CouncilServiceError(Exception):
    """Base error raised by CouncilService."""


class CouncilValidationError(CouncilServiceError):
    """Raised when council-specific data is invalid."""

    def __init__(self, *, field_name: str, message: str) -> None:
        super().__init__(f"Invalid council field '{field_name}': {message}")
        self.field_name = field_name
        self.message = message


class CouncilService:
    """Application service for council operations."""

    def __init__(
        self,
        *,
        tenant_service: TenantService,
        validation_service: ValidationService,
        reference_resolver: ReferenceResolver,
        composition_service: CompositionService,
    ) -> None:
        self._tenant_service = tenant_service
        self._validation_service = validation_service
        self._reference_resolver = reference_resolver
        self._composition_service = composition_service

    async def list(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None = None,
        search: str | None = None,
    ) -> list[CompositionSummary]:
        """List councils available in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return await self._composition_service.list(
            workspace_id=workspace_id,
            composition_type="council",
            search=search,
        )

    async def describe(
        self,
        *,
        user_id: str,
        council_id: str,
        requested_workspace_id: str | None = None,
    ) -> CouncilDocument:
        """Return a complete council."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        document = await self._composition_service.describe(
            workspace_id=workspace_id,
            composition_type="council",
            composition_id=council_id,
        )

        return self._to_council_document(document)

    async def create(
        self,
        *,
        user_id: str,
        payload: CouncilCreate,
        requested_workspace_id: str | None = None,
    ) -> CouncilDocument:
        """Create a council after validating all referenced resources."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        normalized = self._normalize_create(payload)

        await self._validate_assignments(
            workspace_id=workspace_id,
            assignments=normalized.assignments,
        )

        created = await self._composition_service.create(
            workspace_id=workspace_id,
            composition_type="council",
            payload=CompositionCreate(
                name=normalized.name,
                description=normalized.description,
                attributes={},
                items=self._serialize_assignments(
                    normalized.assignments,
                ),
            ),
        )

        return self._to_council_document(created)

    async def update(
        self,
        *,
        user_id: str,
        council_id: str,
        payload: CouncilUpdate,
        requested_workspace_id: str | None = None,
    ) -> CouncilDocument:
        """Update a council using optimistic concurrency."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        normalized = self._normalize_update(payload)

        if normalized.assignments is not None:
            await self._validate_assignments(
                workspace_id=workspace_id,
                assignments=normalized.assignments,
            )

        updated = await self._composition_service.update(
            workspace_id=workspace_id,
            composition_type="council",
            composition_id=council_id,
            payload=CompositionUpdate(
                expected_version=normalized.expected_version,
                name=normalized.name,
                description=normalized.description,
                items=(
                    self._serialize_assignments(
                        normalized.assignments,
                    )
                    if normalized.assignments is not None
                    else None
                ),
            ),
        )

        return self._to_council_document(updated)

    async def delete(
        self,
        *,
        user_id: str,
        council_id: str,
        requested_workspace_id: str | None = None,
    ) -> None:
        """Delete a council when no loop depends on it."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        await self._composition_service.delete(
            workspace_id=workspace_id,
            composition_type="council",
            composition_id=council_id,
        )

    async def _validate_assignments(
        self,
        *,
        workspace_id: str,
        assignments: Sequence[CouncilAssignment],
    ) -> None:
        if not assignments:
            raise CouncilValidationError(
                field_name="assignments",
                message="must contain at least one assignment",
            )

        assignment_keys: list[str] = []
        references: list[ResourceReference] = []

        for index, assignment in enumerate(assignments):
            assignment_keys.append(
                f"{assignment.role}:{assignment.persona_id}",
            )
            references.append(
                ResourceReference(
                    resource_type="persona",
                    resource_id=assignment.persona_id,
                )
            )

            self._validation_service.require_distinct(
                values=list(assignment.skill_ids),
                field_name=f"assignments[{index}].skill_ids",
            )

            references.extend(
                ResourceReference(
                    resource_type="skill",
                    resource_id=skill_id,
                )
                for skill_id in assignment.skill_ids
            )

        self._validation_service.require_distinct(
            values=assignment_keys,
            field_name="assignments",
        )

        await self._reference_resolver.require_many(
            workspace_id=workspace_id,
            references=references,
        )

    def _normalize_create(
        self,
        payload: CouncilCreate,
    ) -> CouncilCreate:
        if not isinstance(payload, CouncilCreate):
            raise CouncilValidationError(
                field_name="payload",
                message="must be a CouncilCreate",
            )

        return CouncilCreate(
            name=self._require_text(payload.name, "name"),
            description=self._normalize_description(
                payload.description,
            ),
            assignments=self._normalize_assignments(
                payload.assignments,
            ),
        )

    def _normalize_update(
        self,
        payload: CouncilUpdate,
    ) -> CouncilUpdate:
        if not isinstance(payload, CouncilUpdate):
            raise CouncilValidationError(
                field_name="payload",
                message="must be a CouncilUpdate",
            )

        self._require_positive_integer(
            payload.expected_version,
            "expected_version",
        )

        return CouncilUpdate(
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
            assignments=(
                self._normalize_assignments(payload.assignments)
                if payload.assignments is not None
                else None
            ),
        )

    def _normalize_assignments(
        self,
        assignments: Sequence[CouncilAssignment],
    ) -> tuple[CouncilAssignment, ...]:
        if not self._is_sequence(assignments):
            raise CouncilValidationError(
                field_name="assignments",
                message="must be a sequence",
            )

        return tuple(
            self._normalize_assignment(
                assignment,
                index=index,
            )
            for index, assignment in enumerate(assignments)
        )

    def _normalize_assignment(
        self,
        assignment: CouncilAssignment,
        *,
        index: int,
    ) -> CouncilAssignment:
        if not isinstance(assignment, CouncilAssignment):
            raise CouncilValidationError(
                field_name=f"assignments[{index}]",
                message="must be a CouncilAssignment",
            )

        skill_ids = self._normalize_skill_ids(
            assignment.skill_ids,
            index=index,
        )

        if not skill_ids:
            raise CouncilValidationError(
                field_name=f"assignments[{index}].skill_ids",
                message="must contain at least one skill",
            )

        return CouncilAssignment(
            role=self._require_text(
                assignment.role,
                f"assignments[{index}].role",
            ).casefold(),
            persona_id=self._require_text(
                assignment.persona_id,
                f"assignments[{index}].persona_id",
            ),
            skill_ids=skill_ids,
        )

    def _normalize_skill_ids(
        self,
        skill_ids: Sequence[str],
        *,
        index: int,
    ) -> tuple[str, ...]:
        if not self._is_sequence(skill_ids):
            raise CouncilValidationError(
                field_name=f"assignments[{index}].skill_ids",
                message="must be a sequence of strings",
            )

        return tuple(
            self._require_text(
                skill_id,
                f"assignments[{index}].skill_ids[{skill_index}]",
            )
            for skill_index, skill_id in enumerate(skill_ids)
        )

    def _to_council_document(
        self,
        document: CompositionDocument,
    ) -> CouncilDocument:
        if document.composition_type != "council":
            raise CouncilValidationError(
                field_name="document.composition_type",
                message="must be 'council'",
            )

        assignments = tuple(
            self._assignment_from_item(item, index=index)
            for index, item in enumerate(document.items)
        )

        return CouncilDocument(
            id=document.id,
            workspace_id=document.workspace_id,
            name=document.name,
            description=document.description,
            assignments=assignments,
            version=document.version,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    def _assignment_from_item(
        self,
        item: Mapping[str, object],
        *,
        index: int,
    ) -> CouncilAssignment:
        if not isinstance(item, Mapping):
            raise CouncilValidationError(
                field_name=f"document.items[{index}]",
                message="must be an object",
            )

        role = item.get("role")
        persona_id = item.get("persona_id")
        skill_ids = item.get("skill_ids")

        if not isinstance(role, str):
            raise CouncilValidationError(
                field_name=f"document.items[{index}].role",
                message="must be a string",
            )

        if not isinstance(persona_id, str):
            raise CouncilValidationError(
                field_name=f"document.items[{index}].persona_id",
                message="must be a string",
            )

        if not self._is_sequence(skill_ids):
            raise CouncilValidationError(
                field_name=f"document.items[{index}].skill_ids",
                message="must be a sequence",
            )

        assignment = CouncilAssignment(
            role=role,
            persona_id=persona_id,
            skill_ids=tuple(skill_ids),
        )

        return self._normalize_assignment(
            assignment,
            index=index,
        )

    @staticmethod
    def _serialize_assignments(
        assignments: Sequence[CouncilAssignment],
    ) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "role": assignment.role,
                "persona_id": assignment.persona_id,
                "skill_ids": list(assignment.skill_ids),
            }
            for assignment in assignments
        )

    async def _resolve_workspace_id(
        self,
        *,
        user_id: str,
        requested_workspace_id: str | None,
    ) -> str:
        tenant = await self._tenant_service.resolve(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return tenant.workspace_id

    @staticmethod
    def _normalize_description(value: str) -> str:
        if not isinstance(value, str):
            raise CouncilValidationError(
                field_name="description",
                message="must be a string",
            )

        return value.strip()

    @staticmethod
    def _require_positive_integer(
        value: int,
        field_name: str,
    ) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise CouncilValidationError(
                field_name=field_name,
                message="must be an integer greater than zero",
            )

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        if not isinstance(value, str):
            raise CouncilValidationError(
                field_name=field_name,
                message="must be a string",
            )

        normalized = value.strip()

        if not normalized:
            raise CouncilValidationError(
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
