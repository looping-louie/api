"""Filesystem and manifest helpers for packaged instruction catalogs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .instructions import (
    CatalogInstructionType,
    build_builtin_instruction_id,
)


class CatalogLoadError(RuntimeError):
    """Raised when a packaged instruction catalog is invalid."""


@dataclass(frozen=True, slots=True)
class LoadedCatalogResource:
    """Validated manifest data paired with its Markdown content."""

    manifest: Mapping[str, Any]
    content_path: Path
    content: str
    checksum: str


def load_catalog_resources(
    *,
    catalog_dir: Path,
    instruction_type: CatalogInstructionType,
) -> tuple[LoadedCatalogResource, ...]:
    """Load common manifest fields and explicit Markdown resources."""

    registry_path = catalog_dir / "registry.json"

    try:
        parsed = json.loads(
            registry_path.read_text(encoding="utf-8")
        )
    except FileNotFoundError as exc:
        raise CatalogLoadError(
            f"Catalog registry does not exist: {registry_path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise CatalogLoadError(
            f"Invalid catalog registry JSON in {registry_path}: {exc}"
        ) from exc
    except (OSError, UnicodeError) as exc:
        raise CatalogLoadError(
            f"Could not read catalog registry {registry_path}: {exc}"
        ) from exc

    if not isinstance(parsed, list):
        raise CatalogLoadError(
            f"Catalog registry must contain a JSON array: {registry_path}"
        )

    resources: list[LoadedCatalogResource] = []
    seen_ids: set[str] = set()
    seen_keys: set[str] = set()
    seen_names: set[str] = set()
    seen_paths: set[Path] = set()

    for position, value in enumerate(parsed):
        if not isinstance(value, dict):
            raise CatalogLoadError(
                f"Catalog entry at position {position} must be an object."
            )

        entry = value
        instruction_id = require_text(entry, "id")
        key = require_text(entry, "key")
        name = require_text(entry, "name")
        require_text(entry, "description")
        require_positive_integer(entry, "version")
        require_boolean(entry, "enabled_by_default")

        try:
            expected_id = build_builtin_instruction_id(
                instruction_type,
                key,
            )
        except ValueError as exc:
            raise CatalogLoadError(
                f"Catalog entry '{instruction_id}' has invalid key "
                f"'{key}': {exc}"
            ) from exc

        if instruction_id != expected_id:
            raise CatalogLoadError(
                f"Catalog id '{instruction_id}' must be '{expected_id}'."
            )

        content_path = resolve_content_path(
            catalog_dir=catalog_dir,
            relative_path=require_text(entry, "content_path"),
        )

        if content_path.stem != key:
            raise CatalogLoadError(
                f"Catalog id '{instruction_id}' must reference a Markdown "
                f"file named '{key}.md'."
            )

        _require_unique(
            value=instruction_id,
            seen=seen_ids,
            label="id",
        )
        _require_unique(
            value=key.casefold(),
            seen=seen_keys,
            label="key",
        )
        _require_unique(
            value=name.casefold(),
            seen=seen_names,
            label="name",
        )

        if content_path in seen_paths:
            raise CatalogLoadError(
                f"Duplicate catalog content path: {content_path}"
            )

        seen_paths.add(content_path)
        try:
            content = content_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise CatalogLoadError(
                f"Could not read catalog content {content_path}: {exc}"
            ) from exc

        resources.append(
            LoadedCatalogResource(
                manifest=MappingProxyType(entry),
                content_path=content_path,
                content=content,
                checksum=calculate_checksum(
                    metadata=entry,
                    content=content,
                ),
            )
        )

    return tuple(resources)


def calculate_checksum(
    *,
    metadata: Mapping[str, Any],
    content: str,
) -> str:
    """Hash canonical manifest metadata and exact Markdown content."""

    canonical_metadata = json.dumps(
        metadata,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256()
    digest.update(canonical_metadata.encode("utf-8"))
    digest.update(b"\0")
    digest.update(content.encode("utf-8"))
    return digest.hexdigest()


def require_text(
    entry: Mapping[str, Any],
    field_name: str,
) -> str:
    """Return one required non-empty string."""

    value = entry.get(field_name)

    if not isinstance(value, str) or not value.strip():
        raise CatalogLoadError(
            f"Catalog field '{field_name}' must be a non-empty string."
        )

    return value.strip()


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


def require_heading(
    *,
    resource: LoadedCatalogResource,
    expected_heading: str,
) -> None:
    """Require Markdown content to identify the manifest definition."""

    first_line = next(
        (
            line.strip()
            for line in resource.content.splitlines()
            if line.strip()
        ),
        "",
    )

    if first_line != expected_heading:
        raise CatalogLoadError(
            f"Catalog content '{resource.content_path}' must start with "
            f"'{expected_heading}'."
        )


def resolve_content_path(
    *,
    catalog_dir: Path,
    relative_path: str,
) -> Path:
    """Resolve one manifest path without allowing traversal."""

    relative = Path(relative_path)

    if (
        relative.is_absolute()
        or not relative.parts
        or relative.parts[0] != "content"
        or relative.suffix != ".md"
    ):
        raise CatalogLoadError(
            f"Invalid catalog content path: {relative_path}"
        )

    catalog_root = catalog_dir.resolve()
    content_path = (catalog_dir / relative).resolve()

    try:
        content_path.relative_to(catalog_root)
    except ValueError as exc:
        raise CatalogLoadError(
            f"Catalog content path escapes its catalog: {relative_path}"
        ) from exc

    if not content_path.is_file():
        raise CatalogLoadError(
            f"Catalog content does not exist: {relative_path}"
        )

    return content_path


def _require_unique(
    *,
    value: str,
    seen: set[str],
    label: str,
) -> None:
    if value in seen:
        raise CatalogLoadError(
            f"Duplicate catalog {label}: {value}"
        )

    seen.add(value)
