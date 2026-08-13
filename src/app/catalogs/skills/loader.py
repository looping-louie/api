"""Typed loader for packaged skill definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ..instructions.entries import SkillCatalogEntry
from ..instructions.errors import CatalogLoadError
from ..instructions.resource_loader import (
    load_catalog_resources,
    require_heading,
    require_text,
)
from ..instructions.resource_validation import (
    require_boolean,
    require_mapping,
    require_positive_integer,
    require_string_tuple,
)
from ..instructions.types import (
    AgentRole,
    CatalogInstructionCategory,
    CatalogInstructionType,
    InstructionCatalogMetadata,
    InstructionOrigin,
    ProjectPhase,
    ReviewerStrictnessDefaults,
    SkillArtifact,
    SkillOutput,
    SkillPhase,
)


SKILL_CATALOG_DIR = Path(__file__).parent


def load_skill_catalog(
    catalog_dir: Path = SKILL_CATALOG_DIR,
) -> tuple[SkillCatalogEntry, ...]:
    """Load and fully validate immutable skill definitions."""

    resources = load_catalog_resources(
        catalog_dir=catalog_dir,
        instruction_type=CatalogInstructionType.SKILL,
    )
    entries: list[SkillCatalogEntry] = []

    for resource in resources:
        manifest = resource.manifest
        instruction_id = require_text(manifest, "id")
        name = require_text(manifest, "name")
        require_heading(
            resource=resource,
            expected_heading=f"# {name}",
        )

        try:
            entry = SkillCatalogEntry(
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
                reviewer_default_strictness=_load_strictness(
                    manifest,
                ),
                category=CatalogInstructionCategory(
                    require_text(manifest, "category")
                ),
                phase=SkillPhase(
                    require_text(manifest, "phase")
                ),
                artifacts=tuple(
                    SkillArtifact(value)
                    for value in require_string_tuple(
                        manifest,
                        "artifacts",
                        allow_empty=False,
                    )
                ),
                output=SkillOutput(
                    require_text(manifest, "output")
                ),
            )
        except (TypeError, ValueError) as exc:
            raise CatalogLoadError(
                f"Invalid skill '{instruction_id}': {exc}"
            ) from exc

        entries.append(entry)

    return tuple(entries)


def _load_roles(
    manifest: Mapping[str, object],
    field_name: str,
) -> frozenset[AgentRole]:
    """Parse and validate role names from skill manifest metadata."""

    values = require_string_tuple(
        manifest,
        field_name,
        allow_empty=False,
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


def _load_strictness(
    manifest: Mapping[str, object],
) -> ReviewerStrictnessDefaults:
    """Parse reviewer strictness defaults from a skill manifest."""

    field_name = "reviewer_default_strictness"
    values = require_mapping(manifest, field_name)
    expected_phases = {
        phase.value
        for phase in ProjectPhase
    }

    if set(values) != expected_phases:
        raise CatalogLoadError(
            f"Catalog field '{field_name}' must define exactly "
            f"{sorted(expected_phases)}."
        )

    return ReviewerStrictnessDefaults(
        prototype=values["prototype"],
        mvp=values["mvp"],
        production=values["production"],
    )
