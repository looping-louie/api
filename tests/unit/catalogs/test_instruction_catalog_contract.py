from dataclasses import FrozenInstanceError

import pytest

from src.app.catalogs.persona_skills import (
    AgentRole,
    CatalogInstructionType,
    InstructionCatalogMetadata,
    InstructionOrigin,
    PersonaCatalogEntry,
    ReviewerStrictnessDefaults,
    SkillCatalogEntry,
    build_builtin_instruction_id,
)


def build_metadata(
    *roles: AgentRole,
) -> InstructionCatalogMetadata:
    return InstructionCatalogMetadata(
        applies_when=("code", "review"),
        applies_to=frozenset(roles or (AgentRole.REVIEWER,)),
    )


def test_builds_stable_builtin_instruction_ids() -> None:
    assert build_builtin_instruction_id(
        CatalogInstructionType.SKILL,
        "security",
    ) == "builtin:skill:security"
    assert build_builtin_instruction_id(
        CatalogInstructionType.PERSONA,
        "tech_lead",
    ) == "builtin:persona:tech_lead"


def test_builtin_skill_is_immutable_and_not_editable() -> None:
    skill = SkillCatalogEntry(
        id="builtin:skill:security",
        name="Security",
        description="Reviews application security.",
        instructions="Review the supplied work.",
        metadata=build_metadata(AgentRole.REVIEWER),
        origin=InstructionOrigin.BUILTIN,
        enabled_by_default=True,
        catalog_version=1,
        reviewer_default_strictness=ReviewerStrictnessDefaults(
            prototype=40,
            mvp=70,
            production=95,
        ),
    )

    assert skill.instruction_type == CatalogInstructionType.SKILL
    assert skill.editable is False

    with pytest.raises(FrozenInstanceError):
        skill.name = "Changed"  # type: ignore[misc]


def test_custom_skill_can_reference_its_source_without_catalog_version() -> None:
    skill = SkillCatalogEntry(
        id="0ac9ce4f7196499b81353b25e10b6d17",
        name="Workspace security",
        description="Workspace-specific security review.",
        instructions="Apply the workspace security policy.",
        metadata=build_metadata(AgentRole.REVIEWER),
        origin=InstructionOrigin.CUSTOM,
        enabled_by_default=True,
        catalog_version=None,
        source_instruction_id="builtin:skill:security",
    )

    assert skill.editable is True
    assert skill.source_instruction_id == "builtin:skill:security"


def test_marketplace_entry_is_distinct_from_builtin_and_read_only() -> None:
    skill = SkillCatalogEntry(
        id="marketplace-skill-security-pro",
        name="Security Pro",
        description="Marketplace security review.",
        instructions="Apply the marketplace security policy.",
        metadata=build_metadata(AgentRole.REVIEWER),
        origin=InstructionOrigin.MARKETPLACE,
        enabled_by_default=False,
        catalog_version=3,
    )

    assert skill.origin == InstructionOrigin.MARKETPLACE
    assert skill.editable is False


def test_origin_must_use_the_shared_origin_contract() -> None:
    with pytest.raises(ValueError, match="InstructionOrigin"):
        SkillCatalogEntry(
            id="workspace-skill",
            name="Workspace skill",
            description="Workspace-specific review.",
            instructions="Review the supplied work.",
            metadata=build_metadata(AgentRole.REVIEWER),
            origin="custom",  # type: ignore[arg-type]
            enabled_by_default=True,
            catalog_version=None,
        )


def test_builtin_id_must_match_instruction_type() -> None:
    with pytest.raises(
        ValueError,
        match="Builtin instruction IDs",
    ):
        PersonaCatalogEntry(
            id="builtin:skill:tech_lead",
            name="Tech lead",
            description="Leads technical delivery.",
            instructions="Act as the technical lead.",
            metadata=build_metadata(AgentRole.GENERATOR),
            origin=InstructionOrigin.BUILTIN,
            enabled_by_default=True,
            catalog_version=1,
        )


def test_persona_defaults_must_be_supported_roles() -> None:
    with pytest.raises(
        ValueError,
        match="default_for roles",
    ):
        PersonaCatalogEntry(
            id="builtin:persona:tech_lead",
            name="Tech lead",
            description="Leads technical delivery.",
            instructions="Act as the technical lead.",
            metadata=build_metadata(AgentRole.REVIEWER),
            origin=InstructionOrigin.BUILTIN,
            enabled_by_default=True,
            catalog_version=1,
            default_for=frozenset({AgentRole.GENERATOR}),
        )


@pytest.mark.parametrize(
    ("origin", "catalog_version"),
    [
        (InstructionOrigin.BUILTIN, None),
        (InstructionOrigin.BUILTIN, 0),
        (InstructionOrigin.MARKETPLACE, None),
    ],
)
def test_distributed_entries_require_positive_catalog_version(
    origin: InstructionOrigin,
    catalog_version: int | None,
) -> None:
    instruction_id = (
        "builtin:skill:security"
        if origin == InstructionOrigin.BUILTIN
        else "marketplace-skill-security"
    )

    with pytest.raises(ValueError, match="positive catalog_version"):
        SkillCatalogEntry(
            id=instruction_id,
            name="Security",
            description="Reviews security.",
            instructions="Review the supplied work.",
            metadata=build_metadata(AgentRole.REVIEWER),
            origin=origin,
            enabled_by_default=True,
            catalog_version=catalog_version,
        )
