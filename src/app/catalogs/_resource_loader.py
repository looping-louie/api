"""Filesystem helpers shared by packaged instruction catalogs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .instructions import (
    CatalogInstructionType,
    build_builtin_instruction_id,
)


def load_registry(
    *,
    catalog_dir: Path,
    instruction_type: CatalogInstructionType,
) -> list[dict[str, Any]]:
    """Load a manifest and validate identity, names and explicit paths."""

    registry_path = catalog_dir / "registry.json"

    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Catalog registry does not exist: {registry_path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid catalog registry JSON: {exc}"
        ) from exc

    if not isinstance(data, list):
        raise RuntimeError("Catalog registry must contain a JSON array.")

    seen_ids: set[str] = set()
    seen_keys: set[str] = set()
    seen_names: set[str] = set()
    seen_paths: set[Path] = set()

    for entry in data:
        if not isinstance(entry, dict):
            raise RuntimeError(
                "Each catalog registry entry must be an object."
            )

        instruction_id = _require_text(entry, "id")
        key = _require_text(entry, "key")
        name = _require_text(entry, "name")
        expected_id = build_builtin_instruction_id(
            instruction_type,
            key,
        )

        if instruction_id != expected_id:
            raise RuntimeError(
                f"Catalog id '{instruction_id}' must be '{expected_id}'."
            )

        version = entry.get("version")

        if (
            isinstance(version, bool)
            or not isinstance(version, int)
            or version < 1
        ):
            raise RuntimeError(
                f"Catalog entry '{instruction_id}' requires a positive "
                "version."
            )

        if not isinstance(entry.get("enabled_by_default"), bool):
            raise RuntimeError(
                f"Catalog entry '{instruction_id}' requires a boolean "
                "enabled_by_default."
            )

        content_path = resolve_content_path(
            catalog_dir=catalog_dir,
            relative_path=_require_text(entry, "content_path"),
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
            raise RuntimeError(
                f"Duplicate catalog content path: {content_path}"
            )

        seen_paths.add(content_path)

    return data


def load_content(
    *,
    catalog_dir: Path,
    registry: list[dict[str, Any]],
    instruction_id_or_key: str,
) -> str:
    """Load content using an explicit manifest path."""

    requested = instruction_id_or_key.strip()
    matches = [
        entry
        for entry in registry
        if entry["id"] == requested or entry["key"] == requested
    ]

    if not matches:
        raise ValueError(f"Unknown catalog instruction: {requested}")

    if len(matches) > 1:
        raise RuntimeError(
            f"Ambiguous catalog instruction: {requested}"
        )

    content_path = resolve_content_path(
        catalog_dir=catalog_dir,
        relative_path=str(matches[0]["content_path"]),
    )
    return content_path.read_text(encoding="utf-8")


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
        raise RuntimeError(
            f"Invalid catalog content path: {relative_path}"
        )

    catalog_root = catalog_dir.resolve()
    content_path = (catalog_dir / relative).resolve()

    try:
        content_path.relative_to(catalog_root)
    except ValueError as exc:
        raise RuntimeError(
            f"Catalog content path escapes its catalog: {relative_path}"
        ) from exc

    if not content_path.is_file():
        raise RuntimeError(
            f"Catalog content does not exist: {relative_path}"
        )

    return content_path


def _require_text(
    entry: dict[str, Any],
    field_name: str,
) -> str:
    value = entry.get(field_name)

    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(
            f"Catalog field '{field_name}' must be a non-empty string."
        )

    return value.strip()


def _require_unique(
    *,
    value: str,
    seen: set[str],
    label: str,
) -> None:
    if value in seen:
        raise RuntimeError(f"Duplicate catalog {label}: {value}")

    seen.add(value)
