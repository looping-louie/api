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
class LoopModelBinding:
    """Model assigned to one role inside a loop."""

    role: str
    model_id: str


@dataclass(frozen=True, slots=True)
class LoopCreate:
    """Data required to create a loop."""

    name: str
    description: str
    council_id: str
    max_iterations: int
    model_bindings: Sequence[LoopModelBinding]


@dataclass(frozen=True, slots=True)
class LoopUpdate:
    """Partial changes applied to an existing loop."""

    expected_version: int
    name: str | None = None
    description: str | None = None
    council_id: str | None = None
    max_iterations: int | None = None
    model_bindings: Sequence[LoopModelBinding] | None = None


@dataclass(frozen=True, slots=True)
class LoopDocument:
    """Complete loop representation."""

    id: str
    workspace_id: str
    name: str
    description: str
    council_id: str
    max_iterations: int
    model_bindings: tuple[LoopModelBinding, ...]
    version: int
    created_at: datetime
    updated_at: datetime


class LoopServiceError(Exception):
    """Base error raised by LoopService."""


class LoopValidationError(LoopServiceError):
    """Raised when loop-specific data is invalid."""

    def __init__(self, *, field_name: str, message: str) -> None:
        super().__init__(f"Invalid loop field '{field_name}': {message}")
        self.field_name = field_name
        self.message = message


class LoopService:
    """Application service for loop operations."""

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
        """List loops available in the resolved workspace."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        return await self._composition_service.list(
            workspace_id=workspace_id,
            composition_type="loop",
            search=search,
        )

    async def describe(
        self,
        *,
        user_id: str,
        loop_id: str,
        requested_workspace_id: str | None = None,
    ) -> LoopDocument:
        """Return a complete loop."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        document = await self._composition_service.describe(
            workspace_id=workspace_id,
            composition_type="loop",
            composition_id=loop_id,
        )

        return self._to_loop_document(document)

    async def create(
        self,
        *,
        user_id: str,
        payload: LoopCreate,
        requested_workspace_id: str | None = None,
    ) -> LoopDocument:
        """Create a loop after validating its council and models."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        normalized = self._normalize_create(payload)

        await self._validate_configuration(
            workspace_id=workspace_id,
            council_id=normalized.council_id,
            model_bindings=normalized.model_bindings,
        )

        created = await self._composition_service.create(
            workspace_id=workspace_id,
            composition_type="loop",
            payload=CompositionCreate(
                name=normalized.name,
                description=normalized.description,
                attributes={
                    "council_id": normalized.council_id,
                    "max_iterations": normalized.max_iterations,
                },
                items=self._serialize_bindings(
                    normalized.model_bindings,
                ),
            ),
        )

        return self._to_loop_document(created)

    async def update(
        self,
        *,
        user_id: str,
        loop_id: str,
        payload: LoopUpdate,
        requested_workspace_id: str | None = None,
    ) -> LoopDocument:
        """Update a loop using optimistic concurrency."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )
        normalized = self._normalize_update(payload)

        current_document = await self._composition_service.describe(
            workspace_id=workspace_id,
            composition_type="loop",
            composition_id=loop_id,
        )
        current = self._to_loop_document(current_document)

        final_council_id = normalized.council_id or current.council_id
        final_iterations = (
            normalized.max_iterations
            if normalized.max_iterations is not None
            else current.max_iterations
        )
        final_bindings = (
            normalized.model_bindings
            if normalized.model_bindings is not None
            else current.model_bindings
        )

        configuration_changed = (
            normalized.council_id is not None
            or normalized.model_bindings is not None
        )

        if configuration_changed:
            await self._validate_configuration(
                workspace_id=workspace_id,
                council_id=final_council_id,
                model_bindings=final_bindings,
            )

        attributes_changed = (
            normalized.council_id is not None
            or normalized.max_iterations is not None
        )

        updated = await self._composition_service.update(
            workspace_id=workspace_id,
            composition_type="loop",
            composition_id=loop_id,
            payload=CompositionUpdate(
                expected_version=normalized.expected_version,
                name=normalized.name,
                description=normalized.description,
                attributes=(
                    {
                        "council_id": final_council_id,
                        "max_iterations": final_iterations,
                    }
                    if attributes_changed
                    else None
                ),
                items=(
                    self._serialize_bindings(final_bindings)
                    if normalized.model_bindings is not None
                    else None
                ),
            ),
        )

        return self._to_loop_document(updated)

    async def delete(
        self,
        *,
        user_id: str,
        loop_id: str,
        requested_workspace_id: str | None = None,
    ) -> None:
        """Delete a loop without removing historical run snapshots."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        await self._composition_service.delete(
            workspace_id=workspace_id,
            composition_type="loop",
            composition_id=loop_id,
        )

    async def validate(
        self,
        *,
        user_id: str,
        loop_id: str,
        requested_workspace_id: str | None = None,
    ) -> LoopDocument:
        """Validate that a stored loop still has valid references."""

        workspace_id = await self._resolve_workspace_id(
            user_id=user_id,
            requested_workspace_id=requested_workspace_id,
        )

        document = await self._composition_service.describe(
            workspace_id=workspace_id,
            composition_type="loop",
            composition_id=loop_id,
        )
        loop = self._to_loop_document(document)

        await self._validate_configuration(
            workspace_id=workspace_id,
            council_id=loop.council_id,
            model_bindings=loop.model_bindings,
        )

        return loop

    async def _validate_configuration(
        self,
        *,
        workspace_id: str,
        council_id: str,
        model_bindings: Sequence[LoopModelBinding],
    ) -> None:
        self._validation_service.require_distinct(
            values=[
                binding.role
                for binding in model_bindings
            ],
            field_name="model_bindings.roles",
        )

        resolved_council = await self._reference_resolver.require_one(
            workspace_id=workspace_id,
            reference=ResourceReference(
                resource_type="council",
                resource_id=council_id,
            ),
        )

        await self._reference_resolver.require_many(
            workspace_id=workspace_id,
            references=[
                ResourceReference(
                    resource_type="model",
                    resource_id=binding.model_id,
                )
                for binding in model_bindings
            ],
        )

        council_roles = self._extract_council_roles(
            resolved_council.value,
        )
        binding_roles = {
            binding.role
            for binding in model_bindings
        }

        missing_roles = council_roles - binding_roles
        extra_roles = binding_roles - council_roles

        if missing_roles:
            raise LoopValidationError(
                field_name="model_bindings",
                message=(
                    "missing model bindings for roles: "
                    f"{', '.join(sorted(missing_roles))}"
                ),
            )

        if extra_roles:
            raise LoopValidationError(
                field_name="model_bindings",
                message=(
                    "contains bindings for unused roles: "
                    f"{', '.join(sorted(extra_roles))}"
                ),
            )

    def _extract_council_roles(self, value: object) -> set[str]:
        items = self._extract_council_items(value)
        roles: set[str] = set()

        for index, item in enumerate(items):
            if not isinstance(item, Mapping):
                raise LoopValidationError(
                    field_name=f"council.items[{index}]",
                    message="must be an object",
                )

            role = item.get("role")

            if not isinstance(role, str) or not role.strip():
                raise LoopValidationError(
                    field_name=f"council.items[{index}].role",
                    message="must be a non-empty string",
                )

            roles.add(role.strip().casefold())

        if not roles:
            raise LoopValidationError(
                field_name="council",
                message="must contain at least one assigned role",
            )

        return roles

    def _extract_council_items(
        self,
        value: object,
    ) -> Sequence[Mapping[str, object]]:
        if isinstance(value, CompositionDocument):
            if value.composition_type != "council":
                raise LoopValidationError(
                    field_name="council",
                    message="resolved resource is not a council",
                )

            return value.items

        assignments = getattr(value, "assignments", None)

        if self._is_sequence(assignments):
            return tuple(
                {
                    "role": getattr(assignment, "role", None),
                }
                for assignment in assignments
            )

        if isinstance(value, Mapping):
            items = value.get("items")

            if self._is_sequence(items):
                return tuple(items)

        raise LoopValidationError(
            field_name="council",
            message="resolved council has an unsupported representation",
        )

    def _normalize_create(
        self,
        payload: LoopCreate,
    ) -> LoopCreate:
        if not isinstance(payload, LoopCreate):
            raise LoopValidationError(
                field_name="payload",
                message="must be a LoopCreate",
            )

        return LoopCreate(
            name=self._require_text(payload.name, "name"),
            description=self._normalize_description(
                payload.description,
            ),
            council_id=self._require_text(
                payload.council_id,
                "council_id",
            ),
            max_iterations=self._require_positive_integer(
                payload.max_iterations,
                "max_iterations",
            ),
            model_bindings=self._normalize_bindings(
                payload.model_bindings,
            ),
        )

    def _normalize_update(
        self,
        payload: LoopUpdate,
    ) -> LoopUpdate:
        if not isinstance(payload, LoopUpdate):
            raise LoopValidationError(
                field_name="payload",
                message="must be a LoopUpdate",
            )

        self._require_positive_integer(
            payload.expected_version,
            "expected_version",
        )

        return LoopUpdate(
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
            council_id=(
                self._require_text(
                    payload.council_id,
                    "council_id",
                )
                if payload.council_id is not None
                else None
            ),
            max_iterations=(
                self._require_positive_integer(
                    payload.max_iterations,
                    "max_iterations",
                )
                if payload.max_iterations is not None
                else None
            ),
            model_bindings=(
                self._normalize_bindings(payload.model_bindings)
                if payload.model_bindings is not None
                else None
            ),
        )

    def _normalize_bindings(
        self,
        bindings: Sequence[LoopModelBinding],
    ) -> tuple[LoopModelBinding, ...]:
        if not self._is_sequence(bindings):
            raise LoopValidationError(
                field_name="model_bindings",
                message="must be a sequence",
            )

        if not bindings:
            raise LoopValidationError(
                field_name="model_bindings",
                message="must contain at least one binding",
            )

        normalized = tuple(
            self._normalize_binding(binding, index=index)
            for index, binding in enumerate(bindings)
        )

        self._validation_service.require_distinct(
            values=[
                binding.role
                for binding in normalized
            ],
            field_name="model_bindings.roles",
        )

        return normalized

    def _normalize_binding(
        self,
        binding: LoopModelBinding,
        *,
        index: int,
    ) -> LoopModelBinding:
        if not isinstance(binding, LoopModelBinding):
            raise LoopValidationError(
                field_name=f"model_bindings[{index}]",
                message="must be a LoopModelBinding",
            )

        return LoopModelBinding(
            role=self._require_text(
                binding.role,
                f"model_bindings[{index}].role",
            ).casefold(),
            model_id=self._require_text(
                binding.model_id,
                f"model_bindings[{index}].model_id",
            ),
        )

    def _to_loop_document(
        self,
        document: CompositionDocument,
    ) -> LoopDocument:
        if document.composition_type != "loop":
            raise LoopValidationError(
                field_name="document.composition_type",
                message="must be 'loop'",
            )

        council_id = document.attributes.get("council_id")
        max_iterations = document.attributes.get("max_iterations")

        if not isinstance(council_id, str):
            raise LoopValidationError(
                field_name="document.attributes.council_id",
                message="must be a string",
            )

        max_iterations = self._require_positive_integer(
            max_iterations,
            "document.attributes.max_iterations",
        )

        bindings = tuple(
            self._binding_from_item(item, index=index)
            for index, item in enumerate(document.items)
        )

        return LoopDocument(
            id=document.id,
            workspace_id=document.workspace_id,
            name=document.name,
            description=document.description,
            council_id=council_id,
            max_iterations=max_iterations,
            model_bindings=bindings,
            version=document.version,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    def _binding_from_item(
        self,
        item: Mapping[str, object],
        *,
        index: int,
    ) -> LoopModelBinding:
        if not isinstance(item, Mapping):
            raise LoopValidationError(
                field_name=f"document.items[{index}]",
                message="must be an object",
            )

        role = item.get("role")
        model_id = item.get("model_id")

        if not isinstance(role, str):
            raise LoopValidationError(
                field_name=f"document.items[{index}].role",
                message="must be a string",
            )

        if not isinstance(model_id, str):
            raise LoopValidationError(
                field_name=f"document.items[{index}].model_id",
                message="must be a string",
            )

        return self._normalize_binding(
            LoopModelBinding(
                role=role,
                model_id=model_id,
            ),
            index=index,
        )

    @staticmethod
    def _serialize_bindings(
        bindings: Sequence[LoopModelBinding],
    ) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "role": binding.role,
                "model_id": binding.model_id,
            }
            for binding in bindings
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
            raise LoopValidationError(
                field_name="description",
                message="must be a string",
            )

        return value.strip()

    @staticmethod
    def _require_positive_integer(
        value: object,
        field_name: str,
    ) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise LoopValidationError(
                field_name=field_name,
                message="must be an integer greater than zero",
            )

        return value

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        if not isinstance(value, str):
            raise LoopValidationError(
                field_name=field_name,
                message="must be a string",
            )

        normalized = value.strip()

        if not normalized:
            raise LoopValidationError(
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
