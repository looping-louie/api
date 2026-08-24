from datetime import UTC, datetime

import pytest

from src.app.services.persona_skills import DefinitionDocument
from src.app.services.shared.validation import (
    DomainValidationError,
    DuplicateResourceError,
    ResourceVersionConflictError,
    ValidationService,
)
from tests.fakes.instruction_repository import FakeInstructionRepository
from tests.fakes.validation_repository import FakeValidationRepository


def build_service(
    repository: FakeInstructionRepository,
) -> ValidationService:
    return ValidationService(
        repository=FakeValidationRepository(
            instruction_repository=repository,
        )
    )


def seed_persona(
    repository: FakeInstructionRepository,
    *,
    persona_id: str = "persona-1",
    name: str = "Tech Lead",
) -> None:
    now = datetime(2026, 7, 13, tzinfo=UTC)

    repository.seed(
        DefinitionDocument(
            id=persona_id,
            workspace_id="workspace-1",
            instruction_type="persona",
            name=name,
            description="Description",
            instructions="Instructions",
            metadata={},
            version=1,
            created_at=now,
            updated_at=now,
        )
    )


@pytest.mark.asyncio
async def test_require_unique_name_rejects_normalized_duplicate() -> None:
    repository = FakeInstructionRepository()
    seed_persona(repository)
    service = build_service(repository)

    with pytest.raises(DuplicateResourceError):
        await service.require_unique_name(
            workspace_id="workspace-1",
            resource_type="persona",
            name=" tech lead ",
        )


@pytest.mark.asyncio
async def test_require_unique_name_allows_current_resource() -> None:
    repository = FakeInstructionRepository()
    seed_persona(repository)
    service = build_service(repository)

    await service.require_unique_name(
        workspace_id="workspace-1",
        resource_type="persona",
        name="Tech Lead",
        exclude_resource_id="persona-1",
    )


def test_require_expected_version_accepts_current_version() -> None:
    service = build_service(FakeInstructionRepository())

    service.require_expected_version(
        expected_version=2,
        current_version=2,
    )


def test_require_expected_version_rejects_stale_version() -> None:
    service = build_service(FakeInstructionRepository())

    with pytest.raises(ResourceVersionConflictError):
        service.require_expected_version(
            expected_version=1,
            current_version=2,
        )


def test_require_distinct_rejects_case_insensitive_duplicates() -> None:
    service = build_service(FakeInstructionRepository())

    with pytest.raises(DomainValidationError):
        service.require_distinct(
            values=["security", "Accessibility", "SECURITY"],
            field_name="skill_ids",
        )


def test_require_distinct_accepts_unique_values() -> None:
    service = build_service(FakeInstructionRepository())

    service.require_distinct(
        values=["security", "accessibility"],
        field_name="skill_ids",
    )
