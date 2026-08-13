"""Primitive types and shared metadata for instruction catalogs."""

import re
from dataclasses import dataclass
from enum import StrEnum


_CATALOG_KEY_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
CATALOG_INSTRUCTION_PAGE_SIZE = 12


class InstructionOrigin(StrEnum):
    """Ownership and distribution source of an instruction definition."""

    BUILTIN = "builtin"
    CUSTOM = "custom"
    MARKETPLACE = "marketplace"


class CatalogInstructionCategory(StrEnum):
    """Broad company area responsible for a skill or persona."""

    SOFTWARE_ENGINEERING = "software_engineering"
    QUALITY_RELIABILITY = "quality_reliability"
    SECURITY_PRIVACY = "security_privacy"
    DATA_AI = "data_ai"
    PRODUCT_DISCOVERY_STRATEGY = "product_discovery_strategy"
    PRODUCT_DESIGN_UX = "product_design_ux"
    DELIVERY_PLANNING = "delivery_planning"
    CONTENT_BRAND = "content_brand"
    GROWTH_ACQUISITION = "growth_acquisition"
    RESEARCH_ANALYTICS = "research_analytics"
    SALES = "sales"
    CUSTOMER_SUCCESS_SUPPORT = "customer_success_support"


class CatalogInstructionStatus(StrEnum):
    """Workspace availability states accepted by catalog listings."""

    ENABLED = "enabled"
    DISABLED = "disabled"


class CatalogInstructionSort(StrEnum):
    """Supported ordering for skill and persona catalog queries."""

    ALPHABETICAL_ASC = "alphabetical-asc"
    ALPHABETICAL_DESC = "alphabetical-desc"
    NEWEST = "newest"
    OLDEST = "oldest"


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


class SkillPhase(StrEnum):
    """Workflow phases in which packaged skills participate."""

    CODE_REVIEW = "code_review"
    DELIBERATION = "deliberation"
    REVIEW = "review"


class SkillArtifact(StrEnum):
    """Artifacts a packaged skill may inspect."""

    CHANGED_FILES = "changed_files"
    CONTRIBUTIONS = "contributions"
    CURRENT_ARTIFACT = "current_artifact"
    GIT_DIFF = "git_diff"
    PROMPT = "prompt"


class SkillOutput(StrEnum):
    """Output contracts requested by packaged skills."""

    JSON = "json"


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
        """Reject empty applicability criteria and unsupported roles."""

        require_unique_non_empty_strings(
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
        """Require every phase strictness to be an integer percentage."""

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


def require_non_empty_text(value: str, *, field_name: str) -> None:
    """Reject blank values used in instruction catalog contracts."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")


def require_unique_non_empty_strings(
    values: tuple[str, ...],
    *,
    field_name: str,
    allow_empty: bool,
) -> None:
    """Validate an immutable sequence of unique non-empty strings."""

    if not isinstance(values, tuple):
        raise ValueError(f"{field_name} must be a tuple.")

    if not allow_empty and not values:
        raise ValueError(f"{field_name} must not be empty.")

    seen: set[str] = set()

    for value in values:
        require_non_empty_text(value, field_name=field_name)
        comparison_key = value.strip().casefold()

        if comparison_key in seen:
            raise ValueError(
                f"{field_name} must not contain duplicate values."
            )

        seen.add(comparison_key)
