"""Domain contract shared by the skill and persona catalogs.

Catalog entries describe instruction definitions distributed by Looping Louie
or, in the future, by its marketplace. They are deliberately independent from
HTTP schemas, application services and persistence adapters.

Origins have explicit ownership semantics:

* ``builtin`` definitions are shipped with Looping Louie. Their stable ID uses
  ``builtin:{instruction_type}:{key}`` and they are immutable through the API.
* ``custom`` definitions belong to a workspace. They may point to the
  definition they were copied from through ``source_instruction_id``.
* ``marketplace`` definitions are externally distributed catalog entries.

``enabled_by_default`` is only the fallback used when a workspace has no
explicit enablement setting. ``catalog_version`` versions distributed catalog
content, while ``deprecated`` keeps an existing definition resolvable without
offering it for new compositions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


_CATALOG_KEY_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


class InstructionOrigin(StrEnum):
    """Ownership and distribution source of an instruction definition."""

    BUILTIN = "builtin"
    CUSTOM = "custom"
    MARKETPLACE = "marketplace"


class CatalogInstructionType(StrEnum):
    """Instruction kinds supported by the curated catalog."""

    SKILL = "skill"
    PERSONA = "persona"


class AgentRole(StrEnum):
    """Roles that may consume catalog instructions."""

    GENERATOR = "generator"
    REVIEWER = "reviewer"


class ProjectPhase(StrEnum):
    """Project phases for which a skill may provide strictness defaults."""

    PROTOTYPE = "prototype"
    MVP = "mvp"
    PRODUCTION = "production"


def build_builtin_instruction_id(
    instruction_type: CatalogInstructionType,
    key: str,
) -> str:
    """Build the stable identifier of one Looping Louie builtin."""

    normalized_key = key.strip()

    if not _CATALOG_KEY_PATTERN.fullmatch(normalized_key):
        raise ValueError(
            "Builtin instruction keys must use lowercase letters, numbers "
            "and single underscores."
        )

    return (
        f"{InstructionOrigin.BUILTIN.value}:"
        f"{instruction_type.value}:"
        f"{normalized_key}"
    )


@dataclass(frozen=True, slots=True)
class InstructionCatalogMetadata:
    """Metadata shared by skills and personas."""

    applies_when: tuple[str, ...]
    applies_to: frozenset[AgentRole]

    def __post_init__(self) -> None:
        _require_unique_non_empty_strings(
            self.applies_when,
            field_name="metadata.applies_when",
            allow_empty=False,
        )

        if not self.applies_to:
            raise ValueError("metadata.applies_to must not be empty.")

        if any(
            not isinstance(role, AgentRole)
            for role in self.applies_to
        ):
            raise ValueError(
                "metadata.applies_to must contain only AgentRole values."
            )


@dataclass(frozen=True, slots=True)
class ReviewerStrictnessDefaults:
    """Default reviewer strictness for each supported project phase."""

    prototype: int
    mvp: int
    production: int

    def __post_init__(self) -> None:
        for phase in ProjectPhase:
            value = getattr(self, phase.value)

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                or value > 100
            ):
                raise ValueError(
                    f"{phase.value} strictness must be an integer "
                    "between 0 and 100."
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogInstructionEntry:
    """Common immutable representation of one instruction definition.

    API mutability is determined by ``origin``. Builtins and marketplace
    entries are read-only definitions; users customize them by creating a
    separate ``custom`` definition with ``source_instruction_id`` set.
    """

    id: str
    name: str
    description: str
    instructions: str
    metadata: InstructionCatalogMetadata
    origin: InstructionOrigin
    enabled_by_default: bool
    catalog_version: int | None
    deprecated: bool = False
    source_instruction_id: str | None = None

    @property
    def instruction_type(self) -> CatalogInstructionType:
        """Return the concrete instruction kind."""

        raise NotImplementedError

    @property
    def editable(self) -> bool:
        """Return whether the definition may be changed through the API."""

        return self.origin == InstructionOrigin.CUSTOM

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, InstructionCatalogMetadata):
            raise ValueError(
                "metadata must be InstructionCatalogMetadata."
            )

        if not isinstance(self.origin, InstructionOrigin):
            raise ValueError("origin must be an InstructionOrigin.")

        _require_non_empty_text(self.id, field_name="id")
        _require_non_empty_text(self.name, field_name="name")
        _require_non_empty_text(
            self.description,
            field_name="description",
        )
        _require_non_empty_text(
            self.instructions,
            field_name="instructions",
        )

        if not isinstance(self.enabled_by_default, bool):
            raise ValueError("enabled_by_default must be a boolean.")

        if not isinstance(self.deprecated, bool):
            raise ValueError("deprecated must be a boolean.")

        self._validate_origin_contract()

    def _validate_origin_contract(self) -> None:
        if self.origin == InstructionOrigin.BUILTIN:
            expected_id = build_builtin_instruction_id(
                self.instruction_type,
                self.id.rsplit(":", maxsplit=1)[-1],
            )

            if self.id != expected_id:
                raise ValueError(
                    "Builtin instruction IDs must use "
                    f"'{InstructionOrigin.BUILTIN.value}:"
                    f"{self.instruction_type.value}:<key>'."
                )

        if (
            self.origin != InstructionOrigin.CUSTOM
            and self.source_instruction_id is not None
        ):
            raise ValueError(
                "source_instruction_id is only valid for custom "
                "instructions."
            )

        if self.source_instruction_id is not None:
            _require_non_empty_text(
                self.source_instruction_id,
                field_name="source_instruction_id",
            )

            if self.source_instruction_id == self.id:
                raise ValueError(
                    "source_instruction_id must differ from id."
                )

        if self.origin == InstructionOrigin.CUSTOM:
            if self.catalog_version is not None:
                raise ValueError(
                    "Custom instructions must not define catalog_version."
                )
            return

        if (
            isinstance(self.catalog_version, bool)
            or not isinstance(self.catalog_version, int)
            or self.catalog_version < 1
        ):
            raise ValueError(
                "Builtin and marketplace instructions require a positive "
                "catalog_version."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillCatalogEntry(CatalogInstructionEntry):
    """Catalog definition of a reusable skill."""

    reviewer_default_strictness: ReviewerStrictnessDefaults | None = None

    @property
    def instruction_type(self) -> CatalogInstructionType:
        return CatalogInstructionType.SKILL


@dataclass(frozen=True, slots=True, kw_only=True)
class PersonaCatalogEntry(CatalogInstructionEntry):
    """Catalog definition of a persona and its preferred skills."""

    preferred_skill_ids: tuple[str, ...] = field(default_factory=tuple)
    default_for: frozenset[AgentRole] = field(default_factory=frozenset)

    @property
    def instruction_type(self) -> CatalogInstructionType:
        return CatalogInstructionType.PERSONA

    def __post_init__(self) -> None:
        super(PersonaCatalogEntry, self).__post_init__()
        _require_unique_non_empty_strings(
            self.preferred_skill_ids,
            field_name="preferred_skill_ids",
            allow_empty=True,
        )

        if any(
            not isinstance(role, AgentRole)
            for role in self.default_for
        ):
            raise ValueError(
                "default_for must contain only AgentRole values."
            )

        if not self.default_for <= self.metadata.applies_to:
            raise ValueError(
                "default_for roles must also be present in "
                "metadata.applies_to."
            )


def _require_non_empty_text(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")


def _require_unique_non_empty_strings(
    values: tuple[str, ...],
    *,
    field_name: str,
    allow_empty: bool,
) -> None:
    if not isinstance(values, tuple):
        raise ValueError(f"{field_name} must be a tuple.")

    if not allow_empty and not values:
        raise ValueError(f"{field_name} must not be empty.")

    seen: set[str] = set()

    for value in values:
        _require_non_empty_text(value, field_name=field_name)
        comparison_key = value.strip().casefold()

        if comparison_key in seen:
            raise ValueError(
                f"{field_name} must not contain duplicate values."
            )

        seen.add(comparison_key)
