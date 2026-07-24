"""Dependency lookup and deletion guards."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .reference_resolver import ResourceReference


@dataclass(frozen=True, slots=True)
class DependencyUsage:
    """Resource that depends on another workspace resource."""

    source: ResourceReference
    relation: str
    blocking: bool = True


class DependencyRepository(Protocol):
    """Persistence contract required by DependencyChecker."""

    async def find_usages(
        self,
        *,
        workspace_id: str,
        target: ResourceReference,
    ) -> Sequence[DependencyUsage]:
        """
        Return resources that reference the target.

        Historical or informational dependencies should be returned with
        blocking=False.
        """
        ...


class DependencyCheckerError(Exception):
    """Base error raised by DependencyChecker."""


class DependencyValidationError(DependencyCheckerError):
    """Raised when dependency data is invalid."""

    def __init__(self, *, field_name: str, message: str) -> None:
        """Store the invalid dependency field and reason."""

        super().__init__(f"Invalid '{field_name}': {message}")
        self.field_name = field_name
        self.message = message


class ResourceInUseError(DependencyCheckerError):
    """Raised when a resource has blocking dependencies."""

    def __init__(
        self,
        *,
        workspace_id: str,
        target: ResourceReference,
        usages: Sequence[DependencyUsage],
    ) -> None:
        """Describe the references preventing resource deletion."""

        dependencies = ", ".join(
            (
                f"{usage.source.resource_type} "
                f"'{usage.source.resource_id}' via '{usage.relation}'"
            )
            for usage in usages
        )

        message = (
            f"{target.resource_type.capitalize()} '{target.resource_id}' "
            f"cannot be deleted because it is in use: {dependencies}."
        )

        super().__init__(message)
        self.workspace_id = workspace_id
        self.target = target
        self.usages = tuple(usages)


class DependencyChecker:
    """Finds dependencies and prevents unsafe resource deletion."""

    def __init__(self, *, repository: DependencyRepository) -> None:
        """Store the dependency lookup adapter."""

        self._repository = repository

    async def find_usages(
        self,
        *,
        workspace_id: str,
        target: ResourceReference,
    ) -> list[DependencyUsage]:
        """Return every resource that currently references the target."""

        workspace_id = self._require_text(
            workspace_id,
            "workspace_id",
        )
        target = self._normalize_reference(
            target,
            field_name="target",
        )

        usages = await self._repository.find_usages(
            workspace_id=workspace_id,
            target=target,
        )

        normalized_usages = [
            self._normalize_usage(usage)
            for usage in usages
        ]

        return self._remove_duplicates(normalized_usages)

    async def require_deletable(
        self,
        *,
        workspace_id: str,
        target: ResourceReference,
    ) -> None:
        """Ensure that a resource has no blocking dependencies."""

        normalized_workspace_id = self._require_text(
            workspace_id,
            "workspace_id",
        )
        normalized_target = self._normalize_reference(
            target,
            field_name="target",
        )

        usages = await self.find_usages(
            workspace_id=normalized_workspace_id,
            target=normalized_target,
        )
        blocking_usages = [
            usage
            for usage in usages
            if usage.blocking
        ]

        if blocking_usages:
            raise ResourceInUseError(
                workspace_id=normalized_workspace_id,
                target=normalized_target,
                usages=blocking_usages,
            )

    def _normalize_usage(
        self,
        usage: DependencyUsage,
    ) -> DependencyUsage:
        """Validate and normalize one dependency usage."""

        if not isinstance(usage, DependencyUsage):
            raise DependencyValidationError(
                field_name="usage",
                message="must be a DependencyUsage",
            )

        if not isinstance(usage.blocking, bool):
            raise DependencyValidationError(
                field_name="usage.blocking",
                message="must be a boolean",
            )

        return DependencyUsage(
            source=self._normalize_reference(
                usage.source,
                field_name="usage.source",
            ),
            relation=self._require_text(
                usage.relation,
                "usage.relation",
            ),
            blocking=usage.blocking,
        )

    @classmethod
    def _normalize_reference(
        cls,
        reference: ResourceReference,
        *,
        field_name: str,
    ) -> ResourceReference:
        """Validate and normalize one resource reference."""

        if not isinstance(reference, ResourceReference):
            raise DependencyValidationError(
                field_name=field_name,
                message="must be a ResourceReference",
            )

        return ResourceReference(
            resource_type=cls._require_text(
                reference.resource_type,
                f"{field_name}.resource_type",
            ).casefold(),
            resource_id=cls._require_text(
                reference.resource_id,
                f"{field_name}.resource_id",
            ),
        )

    @staticmethod
    def _remove_duplicates(
        usages: Sequence[DependencyUsage],
    ) -> list[DependencyUsage]:
        """Deduplicate usages while preserving repository order."""

        unique_usages: list[DependencyUsage] = []
        seen: set[tuple[ResourceReference, str, bool]] = set()

        for usage in usages:
            key = (
                usage.source,
                usage.relation,
                usage.blocking,
            )

            if key in seen:
                continue

            seen.add(key)
            unique_usages.append(usage)

        return unique_usages

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        """Return stripped non-empty dependency text."""

        if not isinstance(value, str):
            raise DependencyValidationError(
                field_name=field_name,
                message="must be a string",
            )

        normalized = value.strip()

        if not normalized:
            raise DependencyValidationError(
                field_name=field_name,
                message="must not be empty",
            )

        return normalized
