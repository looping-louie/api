"""Tests for Persona and Skill definition lifecycle services."""

from datetime import UTC, datetime

import pytest

from src.app.catalogs.persona_skills import InstructionOrigin
from src.app.services.persona_skills import (
    AvailableDefinitionDocument,
    BuiltinDefinitionImmutableError,
    DefinitionCreate,
    DefinitionDisabledError,
    DefinitionNotOwnedError,
    DefinitionType,
    DefinitionUpdate,
    PersonaDefinitionService,
    SkillDefinitionService,
)
from src.app.services.shared.reference_resolver import ResourceReference
from src.app.services.shared.validation import DuplicateResourceError
from tests.fakes.dependency_checker import FakeDependencyChecker, FakeResourceInUseError
from tests.fakes.instruction_repository import FakeInstructionRepository


def seed_builtin(
    repository: FakeInstructionRepository,
    *,
    instruction_type: DefinitionType,
) -> AvailableDefinitionDocument:
    """Seed one selectable built-in definition."""

    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    document = AvailableDefinitionDocument(
        id=f"builtin:{instruction_type}:security",
        project_id="catalog",
        instruction_type=instruction_type,
        origin=InstructionOrigin.BUILTIN,
        owner_project_id=None,
        source_instruction_id=None,
        name="Security",
        description="Builtin security definition.",
        instructions="Review security.",
        metadata={"applies_when": ["security"]},
        enabled=True,
        enabled_by_default=True,
        deprecated=False,
        catalog_version=1,
        checksum="a" * 64,
        version=1,
        created_at=now,
        updated_at=now,
    )
    repository.seed_available(document)
    return document


@pytest.mark.asyncio
async def test_persona_definition_lifecycle_is_independent(
    persona_definition_service: PersonaDefinitionService,
) -> None:
    """Persona definitions can be created without creating any skills."""

    created = await persona_definition_service.create(
        project_id="workspace-1",
        payload=DefinitionCreate(
            name="  Tech Lead  ",
            description="  Reviews architecture  ",
            instructions="  Review the proposed architecture.  ",
        ),
    )
    described = await persona_definition_service.describe(
        project_id="workspace-1",
        instruction_id=created.id,
    )

    assert created.id == "persona-1"
    assert created.name == "Tech Lead"
    assert described.origin == InstructionOrigin.CUSTOM


@pytest.mark.asyncio
async def test_skill_definition_rejects_duplicate_names(
    skill_definition_service: SkillDefinitionService,
) -> None:
    """Skill definitions enforce their own workspace name uniqueness."""

    payload = DefinitionCreate(
        name="Security",
        description="Security review",
        instructions="Review security.",
    )
    await skill_definition_service.create(project_id="workspace-1", payload=payload)

    with pytest.raises(DuplicateResourceError):
        await skill_definition_service.create(project_id="workspace-1", payload=payload)


@pytest.mark.asyncio
async def test_builtin_definition_can_be_toggled_but_not_mutated(
    persona_definition_service: PersonaDefinitionService,
    instruction_repository: FakeInstructionRepository,
) -> None:
    """Built-in Personas remain immutable while allowing workspace enablement."""

    builtin = seed_builtin(instruction_repository, instruction_type="persona")
    disabled = await persona_definition_service.disable(
        project_id="workspace-1",
        instruction_id=builtin.id,
    )

    assert not disabled.enabled
    with pytest.raises(DefinitionDisabledError):
        await persona_definition_service.resolve_for_selection(
            project_id="workspace-1",
            instruction_id=builtin.id,
        )
    with pytest.raises(BuiltinDefinitionImmutableError):
        await persona_definition_service.delete(
            project_id="workspace-1",
            instruction_id=builtin.id,
        )


@pytest.mark.asyncio
async def test_skill_definition_checks_dependencies_before_deletion(
    skill_definition_service: SkillDefinitionService,
    dependency_checker: FakeDependencyChecker,
) -> None:
    """Skill deletion preserves dependency protection."""

    created = await skill_definition_service.create(
        project_id="workspace-1",
        payload=DefinitionCreate(
            name="Accessibility",
            description="Accessibility review",
            instructions="Review accessibility.",
        ),
    )
    dependency_checker.block(
        project_id="workspace-1",
        target=ResourceReference(resource_type="skill", resource_id=created.id),
    )

    with pytest.raises(FakeResourceInUseError):
        await skill_definition_service.delete(
            project_id="workspace-1",
            instruction_id=created.id,
        )
    with pytest.raises(DefinitionNotOwnedError):
        await skill_definition_service.update(
            project_id="workspace-2",
            instruction_id=created.id,
            payload=DefinitionUpdate(expected_version=1),
        )
