"""Immutable skill and persona entries in the instruction catalog."""

import re
from dataclasses import dataclass, field

from ..library import LibraryCategory
from .types import (
    AgentRole,
    CatalogInstructionType,
    InstructionCatalogMetadata,
    InstructionOrigin,
    ReviewerStrictnessDefaults,
    SkillArtifact,
    SkillOutput,
    SkillPhase,
    build_builtin_instruction_id,
    require_non_empty_text,
    require_unique_non_empty_strings,
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
    key: str | None = None
    content_path: str | None = None
    checksum: str | None = None
    category: LibraryCategory | None = None

    @property
    def instruction_type(self) -> CatalogInstructionType:
        """Return the concrete instruction kind."""

        raise NotImplementedError

    @property
    def editable(self) -> bool:
        """Return whether the definition may be changed through the API."""

        return self.origin == InstructionOrigin.CUSTOM

    def __post_init__(self) -> None:
        """Validate fields shared by every instruction origin and type."""

        if not isinstance(self.metadata, InstructionCatalogMetadata):
            raise ValueError(
                "metadata must be InstructionCatalogMetadata."
            )

        if not isinstance(self.origin, InstructionOrigin):
            raise ValueError("origin must be an InstructionOrigin.")

        require_non_empty_text(self.id, field_name="id")
        require_non_empty_text(self.name, field_name="name")
        require_non_empty_text(
            self.description,
            field_name="description",
        )
        require_non_empty_text(
            self.instructions,
            field_name="instructions",
        )

        if not isinstance(self.enabled_by_default, bool):
            raise ValueError("enabled_by_default must be a boolean.")

        if not isinstance(self.deprecated, bool):
            raise ValueError("deprecated must be a boolean.")

        if self.category is not None and not isinstance(
            self.category,
            LibraryCategory,
        ):
            raise ValueError("category must be a LibraryCategory.")

        if self.key is not None:
            require_non_empty_text(self.key, field_name="key")

        if self.content_path is not None:
            require_non_empty_text(
                self.content_path,
                field_name="content_path",
            )

        if self.checksum is not None and not re.fullmatch(
            r"[0-9a-f]{64}",
            self.checksum,
        ):
            raise ValueError(
                "checksum must be a lowercase SHA-256 hexadecimal digest."
            )

        self._validate_origin_contract()

    def _validate_origin_contract(self) -> None:
        """Enforce ownership, identity, and version rules for the origin."""

        if self.origin == InstructionOrigin.BUILTIN:
            catalog_key = (
                self.key
                if self.key is not None
                else self.id.rsplit(":", maxsplit=1)[-1]
            )
            expected_id = build_builtin_instruction_id(
                self.instruction_type,
                catalog_key,
            )

            if self.id != expected_id:
                raise ValueError(
                    "Builtin instruction IDs and keys must use "
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
            require_non_empty_text(
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
    phase: SkillPhase | None = None
    artifacts: tuple[SkillArtifact, ...] = field(default_factory=tuple)
    output: SkillOutput | None = None

    @property
    def instruction_type(self) -> CatalogInstructionType:
        """Identify this entry as a reusable skill."""

        return CatalogInstructionType.SKILL

    def __post_init__(self) -> None:
        """Validate skill-specific metadata after shared catalog fields."""

        super(SkillCatalogEntry, self).__post_init__()

        if self.phase is not None and not isinstance(
            self.phase,
            SkillPhase,
        ):
            raise ValueError("phase must be a SkillPhase.")

        if any(
            not isinstance(artifact, SkillArtifact)
            for artifact in self.artifacts
        ):
            raise ValueError(
                "artifacts must contain only SkillArtifact values."
            )

        if self.output is not None and not isinstance(
            self.output,
            SkillOutput,
        ):
            raise ValueError("output must be a SkillOutput.")


@dataclass(frozen=True, slots=True, kw_only=True)
class PersonaCatalogEntry(CatalogInstructionEntry):
    """Catalog definition of a persona and its associated skills."""

    skill_ids: tuple[str, ...] = field(default_factory=tuple)
    default_for: frozenset[AgentRole] = field(default_factory=frozenset)

    @property
    def instruction_type(self) -> CatalogInstructionType:
        """Identify this entry as a persona."""

        return CatalogInstructionType.PERSONA

    def __post_init__(self) -> None:
        """Validate persona skill associations and default roles."""

        super(PersonaCatalogEntry, self).__post_init__()

        require_unique_non_empty_strings(
            self.skill_ids,
            field_name="skill_ids",
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
