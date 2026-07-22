"""Reference lookup adapter for instructions, compositions and models."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.app.services.shared.composition_service import (
    CompositionRepository,
)
from src.app.services.shared.instruction_service import (
    InstructionRepository,
)
from src.app.services.model_service import ModelCatalogService


_INSTRUCTION_TYPES = frozenset(
    {
        "persona",
        "skill",
    }
)

_COMPOSITION_TYPES = frozenset(
    {
        "council",
        "loop",
    }
)

_SUPPORTED_RESOURCE_TYPES = (
    _INSTRUCTION_TYPES
    | _COMPOSITION_TYPES
    | {"model"}
)


class CompositeReferenceRepository:
    """Resolves references through the repositories owning each resource."""

    def __init__(
        self,
        *,
        instruction_repository: InstructionRepository,
        composition_repository: CompositionRepository,
        model_catalog_service: ModelCatalogService,
    ) -> None:
        self._instruction_repository = instruction_repository
        self._composition_repository = composition_repository
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

        if resource_type in _COMPOSITION_TYPES:
            return await self._get_compositions(
                workspace_id=workspace_id,
                composition_type=resource_type,
                composition_ids=unique_ids,
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
        resources: dict[str, Any] = {}

        for instruction_id in instruction_ids:
            document = await self._instruction_repository.get(
                workspace_id=workspace_id,
                instruction_type=instruction_type,
                instruction_id=instruction_id,
            )

            if document is not None:
                resources[instruction_id] = document

        return resources

    async def _get_compositions(
        self,
        *,
        workspace_id: str,
        composition_type: str,
        composition_ids: Sequence[str],
    ) -> dict[str, Any]:
        resources: dict[str, Any] = {}

        for composition_id in composition_ids:
            document = await self._composition_repository.get(
                workspace_id=workspace_id,
                composition_type=composition_type,
                composition_id=composition_id,
            )

            if document is not None:
                resources[composition_id] = document

        return resources

    @staticmethod
    def _unique_ids(
        resource_ids: Sequence[str],
    ) -> tuple[str, ...]:
        unique_ids: list[str] = []
        seen: set[str] = set()

        for resource_id in resource_ids:
            normalized_id = resource_id.strip()

            if not normalized_id or normalized_id in seen:
                continue

            seen.add(normalized_id)
            unique_ids.append(normalized_id)

        return tuple(unique_ids)
