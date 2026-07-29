"""Reference lookup adapter for instructions and models."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.app.services.shared.instruction import (
    InstructionRepository,
)
from src.app.services.models.service import ModelCatalogService


_INSTRUCTION_TYPES = frozenset(
    {
        "persona",
        "skill",
    }
)

_SUPPORTED_RESOURCE_TYPES = (
    _INSTRUCTION_TYPES
    | {"model"}
)


class CompositeReferenceRepository:
    """Resolves references through the repositories owning each resource."""

    def __init__(
        self,
        *,
        instruction_repository: InstructionRepository,
        model_catalog_service: ModelCatalogService,
    ) -> None:
        """Store the instruction and model lookup dependencies."""

        self._instruction_repository = instruction_repository
        self._model_catalog_service = model_catalog_service

    async def get_many(
        self,
        *,
        workspace_id: str,
        resource_type: str,
        resource_ids: Sequence[str],
    ) -> Mapping[str, Any]:
        """Return existing resources indexed by their requested IDs."""

        if resource_type not in _SUPPORTED_RESOURCE_TYPES:
            raise ValueError(
                f"Unsupported resource type '{resource_type}'."
            )

        unique_ids = self._unique_ids(resource_ids)

        if resource_type in _INSTRUCTION_TYPES:
            return await self._get_instructions(
                workspace_id=workspace_id,
                instruction_type=resource_type,
                instruction_ids=unique_ids,
            )

        return self._model_catalog_service.get_many(
            model_ids=unique_ids,
        )

    async def _get_instructions(
        self,
        *,
        workspace_id: str,
        instruction_type: str,
        instruction_ids: Sequence[str],
    ) -> dict[str, Any]:
        """Return selectable instructions by identifier."""

        resources: dict[str, Any] = {}
        get_available = (
            self._instruction_repository.get_available_for_workspace
        )

        for instruction_id in instruction_ids:
            document = await get_available(
                workspace_id=workspace_id,
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

            if document is not None and document.selectable:
                resources[instruction_id] = document

        return resources

    @staticmethod
    def _unique_ids(
        resource_ids: Sequence[str],
    ) -> tuple[str, ...]:
        """Strip and deduplicate identifiers while preserving order."""

        unique_ids: list[str] = []
        seen: set[str] = set()

        for resource_id in resource_ids:
            normalized_id = resource_id.strip()

            if not normalized_id or normalized_id in seen:
                continue

            seen.add(normalized_id)
            unique_ids.append(normalized_id)

        return tuple(unique_ids)
