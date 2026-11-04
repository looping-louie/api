"""Cross-resource reference resolution and validation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence


@dataclass(frozen=True, slots=True)
class ResourceReference:
    """Reference to a domain resource belonging to a workspace."""

    resource_type: str
    resource_id: str


@dataclass(frozen=True, slots=True)
class ResolvedReference:
    """Reference paired with its resolved domain value."""

    reference: ResourceReference
    value: object


class ReferenceRepository(Protocol):
    """Persistence contract required by ReferenceResolver."""

    async def get_many(
        self,
        *,
        project_id: str,
        resource_type: str,
        resource_ids: Sequence[str],
    ) -> Mapping[str, object]:
        """
        Return resources indexed by their identifier.

        Missing resources must simply be omitted from the returned mapping.
        Every returned resource must be visible to the requested workspace.
        """
        ...


class ReferenceResolverError(Exception):
    """Base error raised by ReferenceResolver."""


class ReferenceValidationError(ReferenceResolverError):
    """Raised when a reference or workspace identifier is invalid."""

    def __init__(self, *, field_name: str, message: str) -> None:
        """Store the invalid reference field and reason."""

        super().__init__(f"Invalid '{field_name}': {message}")
        self.field_name = field_name
        self.message = message


class ResourceNotFoundError(ReferenceResolverError):
    """Raised when one or more referenced resources cannot be found."""

    def __init__(
        self,
        *,
        project_id: str,
        references: Sequence[ResourceReference],
    ) -> None:
        """Describe every reference missing from the workspace."""

        missing = ", ".join(
            f"{reference.resource_type} '{reference.resource_id}'"
            for reference in references
        )
        super().__init__(
            f"Referenced resources were not found in workspace "
            f"'{project_id}': {missing}."
        )
        self.project_id = project_id
        self.references = tuple(references)


class ReferenceResolver:
    """Resolves and validates references between workspace resources."""

    def __init__(self, *, repository: ReferenceRepository) -> None:
        """Store the reference lookup adapter."""

        self._repository = repository

    async def require_many(
        self,
        *,
        project_id: str,
        references: Sequence[ResourceReference],
    ) -> list[ResolvedReference]:
        """
        Resolve several references while preserving their input order.

        Repository queries are grouped by resource type and duplicate
        references are only fetched once.
        """

        project_id = self._require_text(
            project_id,
            "project_id",
        )
        normalized_references = [
            self._normalize_reference(reference)
            for reference in references
        ]

        if not normalized_references:
            return []

        grouped_ids = self._group_reference_ids(normalized_references)
        values_by_reference = await self._load_references(
            project_id=project_id,
            grouped_ids=grouped_ids,
        )

        missing = self._find_missing_references(
            references=normalized_references,
            values_by_reference=values_by_reference,
        )

        if missing:
            raise ResourceNotFoundError(
                project_id=project_id,
                references=missing,
            )

        return [
            ResolvedReference(
                reference=reference,
                value=values_by_reference[reference],
            )
            for reference in normalized_references
        ]

    async def _load_references(
        self,
        *,
        project_id: str,
        grouped_ids: Mapping[str, Sequence[str]],
    ) -> dict[ResourceReference, object]:
        """Load grouped resource identifiers from their owning adapters."""

        values_by_reference: dict[ResourceReference, object] = {}

        for resource_type, resource_ids in grouped_ids.items():
            resources = await self._repository.get_many(
                project_id=project_id,
                resource_type=resource_type,
                resource_ids=resource_ids,
            )

            for resource_id, value in resources.items():
                reference = ResourceReference(
                    resource_type=resource_type,
                    resource_id=resource_id,
                )
                values_by_reference[reference] = value

        return values_by_reference

    @staticmethod
    def _group_reference_ids(
        references: Sequence[ResourceReference],
    ) -> dict[str, list[str]]:
        """Group unique identifiers by normalized resource type."""

        grouped_ids: dict[str, list[str]] = defaultdict(list)
        seen: set[ResourceReference] = set()

        for reference in references:
            if reference in seen:
                continue

            seen.add(reference)
            grouped_ids[reference.resource_type].append(
                reference.resource_id,
            )

        return dict(grouped_ids)

    @staticmethod
    def _find_missing_references(
        *,
        references: Sequence[ResourceReference],
        values_by_reference: Mapping[ResourceReference, object],
    ) -> list[ResourceReference]:
        """Return unique missing references in request order."""

        missing: list[ResourceReference] = []
        seen: set[ResourceReference] = set()

        for reference in references:
            if reference in values_by_reference or reference in seen:
                continue

            seen.add(reference)
            missing.append(reference)

        return missing

    @classmethod
    def _normalize_reference(
        cls,
        reference: ResourceReference,
    ) -> ResourceReference:
        """Validate and normalize one requested reference."""

        if not isinstance(reference, ResourceReference):
            raise ReferenceValidationError(
                field_name="reference",
                message="must be a ResourceReference",
            )

        return ResourceReference(
            resource_type=cls._require_text(
                reference.resource_type,
                "resource_type",
            ).casefold(),
            resource_id=cls._require_text(
                reference.resource_id,
                "resource_id",
            ),
        )

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        """Return stripped non-empty reference text."""

        if not isinstance(value, str):
            raise ReferenceValidationError(
                field_name=field_name,
                message="must be a string",
            )

        normalized = value.strip()

        if not normalized:
            raise ReferenceValidationError(
                field_name=field_name,
                message="must not be empty",
            )

        return normalized
