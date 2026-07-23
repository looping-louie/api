"""Typed loader for packaged persona definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from src.app.catalogs._resource_loader import (
    CatalogLoadError,
    load_catalog_resources,
    require_boolean,
    require_heading,
    require_positive_integer,
    require_string_tuple,
    require_text,
)
from src.app.catalogs.instructions import (
    AgentRole,
    CatalogInstructionType,
    InstructionCatalogMetadata,
    InstructionOrigin,
    PersonaCatalogEntry,
)


PERSONA_CATALOG_DIR = Path(__file__).parent


def load_persona_catalog(
    catalog_dir: Path = PERSONA_CATALOG_DIR,
) -> tuple[PersonaCatalogEntry, ...]:
    """Load and fully validate immutable persona definitions."""

    resources = load_catalog_resources(
        catalog_dir=catalog_dir,
        instruction_type=CatalogInstructionType.PERSONA,
    )
    entries: list[PersonaCatalogEntry] = []

    for resource in resources:
        manifest = resource.manifest
        instruction_id = require_text(manifest, "id")
        name = require_text(manifest, "name")
        require_heading(
            resource=resource,
            expected_heading=f"# Persona: {name}",
        )

        try:
            entry = PersonaCatalogEntry(
                id=instruction_id,
                key=require_text(manifest, "key"),
                name=name,
                description=require_text(
                    manifest,
                    "description",
                ),
                instructions=resource.content,
                content_path=require_text(
                    manifest,
                    "content_path",
                ),
                checksum=resource.checksum,
                metadata=InstructionCatalogMetadata(
                    applies_when=require_string_tuple(
                        manifest,
                        "applies_when",
                        allow_empty=False,
                    ),
                    applies_to=_load_roles(
                        manifest,
                        "applies_to",
                        allow_empty=False,
                    ),
                ),
                origin=InstructionOrigin.BUILTIN,
                enabled_by_default=require_boolean(
                    manifest,
                    "enabled_by_default",
                ),
                catalog_version=require_positive_integer(
                    manifest,
                    "version",
                ),
                preferred_skill_ids=require_string_tuple(
                    manifest,
                    "preferred_skill_ids",
                    allow_empty=True,
                ),
                default_for=_load_roles(
                    manifest,
                    "default_for",
                    allow_empty=True,
                ),
            )
        except (TypeError, ValueError) as exc:
            raise CatalogLoadError(
                f"Invalid persona '{instruction_id}': {exc}"
            ) from exc

        entries.append(entry)

    return tuple(entries)


def load_persona_content(
    persona_id_or_key: str,
    *,
    catalog_dir: Path = PERSONA_CATALOG_DIR,
) -> str:
    """Load one persona using its stable ID or temporary legacy key."""

    requested = persona_id_or_key.strip()

    for entry in load_persona_catalog(catalog_dir):
        if entry.id == requested or entry.key == requested:
            return entry.instructions

    raise ValueError(f"Unknown persona: {requested}")


def _load_roles(
    manifest: Mapping[str, object],
    field_name: str,
    *,
    allow_empty: bool,
) -> frozenset[AgentRole]:
    values = require_string_tuple(
        manifest,
        field_name,
        allow_empty=allow_empty,
    )

    try:
        return frozenset(
            AgentRole(value)
            for value in values
        )
    except ValueError as exc:
        raise CatalogLoadError(
            f"Catalog field '{field_name}' contains unsupported role."
        ) from exc
