"""Shared validation operations for referenced resources."""

from typing import Protocol
from unicodedata import normalize


class ValidationRepository(Protocol):
    """Persistence contract required by ValidationService."""

    async def find_resource_id_by_name(
        self,
        *,
        workspace_id: str,
        resource_type: str,
        normalized_name: str,
    ) -> str | None:
        """
        Find a resource by its normalized name.

        Implementations should query the normalized-name column or equivalent
        case-insensitive representation.
        """
        ...


class ValidationServiceError(Exception):
    """Base error raised by ValidationService."""


class DomainValidationError(ValidationServiceError):
    """Raised when a reusable domain validation fails."""

    def __init__(self, *, field_name: str, message: str) -> None:
        super().__init__(f"Invalid '{field_name}': {message}")
        self.field_name = field_name
        self.message = message


class DuplicateResourceError(ValidationServiceError):
    """Raised when a workspace already contains a resource with the name."""

    def __init__(
        self,
        *,
        workspace_id: str,
        resource_type: str,
        name: str,
        existing_resource_id: str,
    ) -> None:
        message = (
            f"A {resource_type} named '{name}' already exists in workspace "
            f"'{workspace_id}'."
        )
        super().__init__(message)
        self.workspace_id = workspace_id
        self.resource_type = resource_type
        self.name = name
        self.existing_resource_id = existing_resource_id


class ResourceVersionConflictError(ValidationServiceError):
    """Raised when optimistic concurrency validation fails."""

    def __init__(
        self,
        *,
        expected_version: int,
        current_version: int,
    ) -> None:
        message = (
            f"Resource has version {current_version}; expected version "
            f"{expected_version}."
        )
        super().__init__(message)
        self.expected_version = expected_version
        self.current_version = current_version


class ValidationService:
    """Reusable validations shared by domain services."""

    def __init__(self, *, repository: ValidationRepository) -> None:
        self._repository = repository

    async def require_unique_name(
        self,
        *,
        workspace_id: str,
        resource_type: str,
        name: str,
        exclude_resource_id: str | None = None,
    ) -> None:
        """Ensure that a name is unique inside a workspace."""

        workspace_id = self._require_text(workspace_id, "workspace_id")
        resource_type = self._require_text(resource_type, "resource_type")
        name = self._require_text(name, "name")
        exclude_resource_id = self._normalize_optional_text(
            exclude_resource_id,
        )

        existing_resource_id = (
            await self._repository.find_resource_id_by_name(
                workspace_id=workspace_id,
                resource_type=resource_type,
                normalized_name=self.normalize_name(name),
            )
        )

        if existing_resource_id is None:
            return

        if existing_resource_id == exclude_resource_id:
            return

        raise DuplicateResourceError(
            workspace_id=workspace_id,
            resource_type=resource_type,
            name=name,
            existing_resource_id=existing_resource_id,
        )

    def require_expected_version(
        self,
        *,
        expected_version: int,
        current_version: int,
    ) -> None:
        """Ensure that an update is based on the current resource version."""

        self._require_positive_integer(
            expected_version,
            "expected_version",
        )
        self._require_positive_integer(
            current_version,
            "current_version",
        )

        if expected_version != current_version:
            raise ResourceVersionConflictError(
                expected_version=expected_version,
                current_version=current_version,
            )

    def require_distinct(
        self,
        *,
        values: list[str],
        field_name: str,
    ) -> None:
        """Ensure that a collection contains no duplicate identifiers."""

        field_name = self._require_text(field_name, "field_name")
        duplicates = self._find_duplicates(values)

        if duplicates:
            duplicate_values = ", ".join(duplicates)
            raise DomainValidationError(
                field_name=field_name,
                message=f"contains duplicate values: {duplicate_values}",
            )

    @staticmethod
    def normalize_name(name: str) -> str:
        """Produce the canonical value used for name uniqueness checks."""

        return normalize("NFKC", name).strip().casefold()

    @classmethod
    def _find_duplicates(cls, values: list[str]) -> list[str]:
        seen: set[str] = set()
        duplicate_keys: set[str] = set()
        duplicates: list[str] = []

        for value in values:
            normalized_value = cls._require_text(value, "value")
            comparison_key = normalize("NFKC", normalized_value).casefold()

            if comparison_key in seen and comparison_key not in duplicate_keys:
                duplicate_keys.add(comparison_key)
                duplicates.append(normalized_value)

            seen.add(comparison_key)

        return duplicates

    @staticmethod
    def _require_positive_integer(value: int, field_name: str) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise DomainValidationError(
                field_name=field_name,
                message="must be an integer greater than zero",
            )

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        if not isinstance(value, str):
            raise DomainValidationError(
                field_name=field_name,
                message="must be a string",
            )

        normalized = value.strip()

        if not normalized:
            raise DomainValidationError(
                field_name=field_name,
                message="must not be empty",
            )

        return normalized

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None
