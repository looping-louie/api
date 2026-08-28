"""Shared deterministic fixtures for unit and controller tests."""

from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Callable
from unittest.mock import MagicMock

import pytest

from src.app.controllers.user import UserController
from src.app.services.models.availability import ModelAvailabilityService
from src.app.services.models.catalog import ModelCatalogService
from src.app.services.users import UserService
from src.app.services.persona_skills import (
    PersonaDefinitionService,
    SkillDefinitionService,
)
from src.app.services.shared.reference_resolver import ReferenceResolver
from src.app.services.shared.tenant import (
    TenantService,
    ProjectMembership,
)
from src.app.services.shared.validation import ValidationService
from tests.fakes.dependency_checker import FakeDependencyChecker
from tests.fakes.dependency_repository import FakeDependencyRepository
from tests.fakes.instruction_repository import FakeInstructionRepository
from tests.fakes.provider_state_repository import (
    FakeProviderStateRepository,
)
from tests.fakes.reference_repository import FakeReferenceRepository
from tests.fakes.tenant_repository import FakeTenantRepository
from tests.fakes.validation_repository import FakeValidationRepository


class IncrementingClock:
    """Deterministic clock that advances one second per call."""

    def __init__(self) -> None:
        self._current = datetime(
            2026,
            7,
            13,
            10,
            0,
            tzinfo=UTC,
        )

    def __call__(self) -> datetime:
        current = self._current
        self._current += timedelta(seconds=1)
        return current


@pytest.fixture
def instruction_repository() -> FakeInstructionRepository:
    return FakeInstructionRepository()


@pytest.fixture
def reference_repository() -> FakeReferenceRepository:
    return FakeReferenceRepository()


@pytest.fixture
def dependency_repository() -> FakeDependencyRepository:
    return FakeDependencyRepository()


@pytest.fixture
def dependency_checker() -> FakeDependencyChecker:
    return FakeDependencyChecker()


@pytest.fixture
def provider_state_repository() -> FakeProviderStateRepository:
    return FakeProviderStateRepository()


@pytest.fixture
def tenant_repository() -> FakeTenantRepository:
    return FakeTenantRepository(
        [
            ProjectMembership(
                user_id="user-1",
                project_id="workspace-1",
                is_default=True,
            ),
        ]
    )


@pytest.fixture
def tenant_service(
    tenant_repository: FakeTenantRepository,
) -> TenantService:
    return TenantService(
        repository=tenant_repository,
    )


@pytest.fixture
def validation_service(
    instruction_repository: FakeInstructionRepository,
) -> ValidationService:
    repository = FakeValidationRepository(
        instruction_repository=instruction_repository,
    )

    return ValidationService(
        repository=repository,
    )


@pytest.fixture
def reference_resolver(
    reference_repository: FakeReferenceRepository,
) -> ReferenceResolver:
    return ReferenceResolver(
        repository=reference_repository,
    )


@pytest.fixture
def persona_definition_service(
    instruction_repository: FakeInstructionRepository,
    validation_service: ValidationService,
    dependency_checker: FakeDependencyChecker,
) -> PersonaDefinitionService:
    """Create a deterministic Persona definition lifecycle service."""

    identifier_counter = count(1)

    def create_identifier() -> str:
        return f"persona-{next(identifier_counter)}"

    clock: Callable[[], datetime] = IncrementingClock()

    return PersonaDefinitionService(
        repository=instruction_repository,
        validation_service=validation_service,
        dependency_checker=dependency_checker,
        id_factory=create_identifier,
        clock=clock,
    )


@pytest.fixture
def skill_definition_service(
    instruction_repository: FakeInstructionRepository,
    validation_service: ValidationService,
    dependency_checker: FakeDependencyChecker,
) -> SkillDefinitionService:
    """Create a deterministic Skill definition lifecycle service."""

    identifier_counter = count(1)

    def create_identifier() -> str:
        return f"skill-{next(identifier_counter)}"

    clock: Callable[[], datetime] = IncrementingClock()

    return SkillDefinitionService(
        repository=instruction_repository,
        validation_service=validation_service,
        dependency_checker=dependency_checker,
        id_factory=create_identifier,
        clock=clock,
    )
@pytest.fixture
def model_availability_service(
    provider_state_repository: FakeProviderStateRepository,
) -> ModelAvailabilityService:
    return ModelAvailabilityService(
        linked_service_repository=provider_state_repository,
    )


@pytest.fixture
def model_catalog_service(
    model_availability_service: ModelAvailabilityService,
) -> ModelCatalogService:
    return ModelCatalogService(
        availability_service=model_availability_service,
    )


@pytest.fixture
def model_controller(
    model_catalog_service: ModelCatalogService,
) -> UserController:
    return UserController(
        service=MagicMock(spec=UserService),
        model_catalog_service=model_catalog_service,
    )
