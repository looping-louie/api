"""Typed value validation for instruction catalog manifests."""

from typing import Any, Mapping

from .errors import CatalogLoadError


def require_string_tuple(
    entry: Mapping[str, Any],
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    """Return a required list of unique non-empty strings."""

    value = entry.get(field_name)

    if not isinstance(value, list):
        raise CatalogLoadError(
            f"Catalog field '{field_name}' must be an array."
        )

    if not allow_empty and not value:
        raise CatalogLoadError(
            f"Catalog field '{field_name}' must not be empty."
        )

    result: list[str] = []
    seen: set[str] = set()

    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise CatalogLoadError(
                f"Catalog field '{field_name}' must contain non-empty "
                "strings."
            )

        normalized = item.strip()
        comparison_key = normalized.casefold()

        if comparison_key in seen:
            raise CatalogLoadError(
                f"Catalog field '{field_name}' contains duplicate value "
                f"'{normalized}'."
            )

        seen.add(comparison_key)
        result.append(normalized)

    return tuple(result)


def require_mapping(
    entry: Mapping[str, Any],
    field_name: str,
) -> Mapping[str, Any]:
    """Return one required JSON object."""

    value = entry.get(field_name)

    if not isinstance(value, dict):
        raise CatalogLoadError(
            f"Catalog field '{field_name}' must be an object."
        )

    return value


def require_positive_integer(
    entry: Mapping[str, Any],
    field_name: str,
) -> int:
    """Return one required positive integer."""

    value = entry.get(field_name)

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
    ):
        raise CatalogLoadError(
            f"Catalog field '{field_name}' must be a positive integer."
        )

    return value


def require_boolean(
    entry: Mapping[str, Any],
    field_name: str,
) -> bool:
    """Return one required boolean."""

    value = entry.get(field_name)

    if not isinstance(value, bool):
        raise CatalogLoadError(
            f"Catalog field '{field_name}' must be a boolean."
        )

    return value
