"""Shared instruction resource operations."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from dataclasses import replace

from src.app.catalogs.persona_skills import (
    CatalogInstructionCategory,
    CatalogInstructionSort,
    CatalogInstructionStatus,
    InstructionOrigin,
)

from ..shared.dependency_checker import DependencyChecker
from ..shared.reference_resolver import ResourceReference
from ..shared.validation import ValidationService
from .types import (
    AvailableDefinitionDocument,
    AvailableDefinitionPage,
    BuiltinDefinitionImmutableError,
    DefinitionCreate,
    DefinitionDisabledError,
    DefinitionDocument,
    DefinitionNotFoundError,
    DefinitionNotOwnedError,
    DefinitionRepository,
    DefinitionType,
    DefinitionUpdate,
    DefinitionVersionConflictError,
    Clock,
    IdFactory,
    copy_available_instruction_document,
    copy_instruction_document,
    default_clock,
    default_id_factory,
)
from .validation import (
    normalize_create,
    normalize_search,
    normalize_update,
    require_instruction_type,
    require_text,
)


class _DefinitionLifecycleService:
    """Shared lifecycle mechanics bound to one definition type."""

    def __init__(
        self,
        *,
        repository: DefinitionRepository,
        validation_service: ValidationService,
        dependency_checker: DependencyChecker,
        instruction_type: DefinitionType,
        id_factory: IdFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._repository = repository
        self._validation_service = validation_service
        self._dependency_checker = dependency_checker
        self._instruction_type = instruction_type
        self._id_factory = id_factory or default_id_factory
        self._clock = clock or default_clock

    async def list(
        self,
        *,
        workspace_id: str,
        search: str | None = None,
        status: CatalogInstructionStatus | None = None,
        categories: Sequence[CatalogInstructionCategory] = (),
        sort: CatalogInstructionSort | None = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> AvailableDefinitionPage:
        """Return a filtered page of the effective instruction catalog."""

        summaries = await self._repository.list_available_for_workspace(
            workspace_id=require_text(workspace_id, "workspace_id"),
            instruction_type=self._instruction_type,
            search=normalize_search(search),
            status=status,
            categories=categories,
            sort=sort,
            offset=offset,
            limit=limit,
        )

        return summaries

    async def describe(
        self,
        *,
        workspace_id: str,
        instruction_id: str,
        include_deprecated: bool = False,
    ) -> AvailableDefinitionDocument:
        """Return a visible instruction, including disabled definitions."""

        document = await self._require_available(
            workspace_id=require_text(workspace_id, "workspace_id"),
            instruction_type=self._instruction_type,
            instruction_id=require_text(instruction_id, "instruction_id"),
            include_deprecated=include_deprecated,
        )

        return copy_available_instruction_document(document)

    async def create(
        self,
        *,
        workspace_id: str,
        payload: DefinitionCreate,
    ) -> DefinitionDocument:
        """Create a workspace-owned custom instruction."""

        workspace_id = require_text(workspace_id, "workspace_id")
        return await self._create_custom(
            workspace_id=workspace_id,
            instruction_type=self._instruction_type,
            payload=payload,
            source_instruction_id=None,
        )

    async def enable(
        self,
        *,
        workspace_id: str,
        instruction_id: str,
    ) -> AvailableDefinitionDocument:
        """Enable a visible instruction for new compositions."""

        return await self._set_enabled(
            workspace_id=workspace_id,
            instruction_type=self._instruction_type,
            instruction_id=instruction_id,
            enabled=True,
        )

    async def disable(
        self,
        *,
        workspace_id: str,
        instruction_id: str,
    ) -> AvailableDefinitionDocument:
        """Disable a visible instruction without hiding its definition."""

        return await self._set_enabled(
            workspace_id=workspace_id,
            instruction_type=self._instruction_type,
            instruction_id=instruction_id,
            enabled=False,
        )

    async def duplicate(
        self,
        *,
        workspace_id: str,
        instruction_id: str,
        name: str | None = None,
    ) -> DefinitionDocument:
        """Fork a visible instruction into a new editable custom copy."""

        workspace_id = require_text(
            workspace_id,
            "workspace_id",
        )
        instruction_id = require_text(
            instruction_id,
            "instruction_id",
        )
        source = await self._require_available(
            workspace_id=workspace_id,
            instruction_type=self._instruction_type,
            instruction_id=instruction_id,
            include_deprecated=False,
        )
        duplicate_name = (
            require_text(name, "name")
            if name is not None
            else f"{source.name} Copy"
        )

        return await self._create_custom(
            workspace_id=workspace_id,
            instruction_type=self._instruction_type,
            payload=DefinitionCreate(
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
        instruction_id: str,
    ) -> AvailableDefinitionDocument:
        """Resolve an instruction that may be used in new compositions."""

        document = await self.describe(
            workspace_id=workspace_id,
            instruction_id=instruction_id,
            include_deprecated=True,
        )

        if not document.selectable:
            raise DefinitionDisabledError(
                instruction_type=self._instruction_type,
                instruction_id=instruction_id,
            )

        return document

    async def update(
        self,
        *,
        workspace_id: str,
        instruction_id: str,
        payload: DefinitionUpdate,
    ) -> DefinitionDocument:
        """Update a persona or skill using optimistic concurrency."""

        workspace_id = require_text(workspace_id, "workspace_id")
        instruction_id = require_text(instruction_id, "instruction_id")

        current = await self._require_owned_custom(
            workspace_id=workspace_id,
            instruction_type=self._instruction_type,
            instruction_id=instruction_id,
        )

        self._validation_service.require_expected_version(
            expected_version=payload.expected_version,
            current_version=current.version,
        )

        normalized = normalize_update(payload)

        if normalized.name is not None:
            await self._validation_service.require_unique_name(
                workspace_id=workspace_id,
                resource_type=self._instruction_type,
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
                instruction_type=self._instruction_type,
                instruction_id=instruction_id,
                expected_version=payload.expected_version,
            )

        return copy_instruction_document(persisted)

    async def delete(
        self,
        *,
        workspace_id: str,
        instruction_id: str,
    ) -> None:
        """Delete a persona or skill after checking its dependencies."""

        workspace_id = require_text(workspace_id, "workspace_id")
        instruction_id = require_text(instruction_id, "instruction_id")

        await self._require_owned_custom(
            workspace_id=workspace_id,
            instruction_type=self._instruction_type,
            instruction_id=instruction_id,
        )

        await self._dependency_checker.require_deletable(
            workspace_id=workspace_id,
            target=ResourceReference(
                resource_type=self._instruction_type,
                resource_id=instruction_id,
            ),
        )

        deleted = await self._repository.delete(
            workspace_id=workspace_id,
            instruction_type=self._instruction_type,
            instruction_id=instruction_id,
        )

        if not deleted:
            raise DefinitionNotFoundError(
                instruction_type=self._instruction_type,
                instruction_id=instruction_id,
            )

    async def _create_custom(
        self,
        *,
        workspace_id: str,
        instruction_type: DefinitionType,
        payload: DefinitionCreate,
        source_instruction_id: str | None,
    ) -> DefinitionDocument:
        normalized = normalize_create(payload)

        await self._validation_service.require_unique_name(
            workspace_id=workspace_id,
            resource_type=instruction_type,
            name=normalized.name,
        )

        now = self._clock()
        document = DefinitionDocument(
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
        return copy_instruction_document(created)

    async def _set_enabled(
        self,
        *,
        workspace_id: str,
        instruction_type: DefinitionType,
        instruction_id: str,
        enabled: bool,
    ) -> AvailableDefinitionDocument:
        require_instruction_type(instruction_type)
        workspace_id = require_text(
            workspace_id,
            "workspace_id",
        )
        instruction_id = require_text(
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
            raise DefinitionDisabledError(
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

        persisted = await self._repository.set_enabled(
            workspace_id=workspace_id,
            instruction_id=instruction_id,
            enabled=enabled,
        )

        if not persisted:
            raise DefinitionNotFoundError(
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
        instruction_type: DefinitionType,
        instruction_id: str,
        include_deprecated: bool,
    ) -> AvailableDefinitionDocument:
        document = await self._repository.get_available_for_workspace(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
            include_deprecated=include_deprecated,
        )

        if document is None:
            raise DefinitionNotFoundError(
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

        return document

    async def _require_owned_custom(
        self,
        *,
        workspace_id: str,
        instruction_type: DefinitionType,
        instruction_id: str,
    ) -> DefinitionDocument:
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
            raise BuiltinDefinitionImmutableError(
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

        document = await self._repository.get_owned_custom(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )

        if document is None:
            raise DefinitionNotOwnedError(
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

        return document

    async def _raise_update_conflict(
        self,
        *,
        workspace_id: str,
        instruction_type: DefinitionType,
        instruction_id: str,
        expected_version: int,
    ) -> None:
        current = await self._repository.get_owned_custom(
            workspace_id=workspace_id,
            instruction_type=instruction_type,
            instruction_id=instruction_id,
        )

        if current is None:
            raise DefinitionNotOwnedError(
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

        raise DefinitionVersionConflictError(
            instruction_type=instruction_type,
            instruction_id=instruction_id,
            expected_version=expected_version,
            current_version=current.version,
        )
