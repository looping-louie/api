from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Callable

import pytest

from src.app.controllers.model import ModelController
from src.app.services.model_service import (
    ModelAvailabilityService,
    ModelCatalogService,
)
from src.app.services.shared.composition_service import CompositionService
from src.app.services.shared.instruction_service import InstructionService
from src.app.services.shared.reference_resolver import ReferenceResolver
from src.app.services.shared.tenant_service import (
    TenantService,
    WorkspaceMembership,
)
from src.app.services.shared.validation_service import ValidationService
from tests.fakes.composition_repository import FakeCompositionRepository
from tests.fakes.dependency_checker import FakeDependencyChecker
from tests.fakes.dependency_repository import FakeDependencyRepository
from tests.fakes.instruction_repository import FakeInstructionRepository
from tests.fakes.provider_state_repository import (
    FakeProviderStateRepository,
)
from tests.fakes.reference_repository import FakeReferenceRepository
from tests.fakes.tenant_repository import FakeTenantRepository
from tests.fakes.validation_repository import FakeValidationRepository
from src.app.controllers.provider import ProviderController
from src.app.services.providers.model_registry_service import (
    StaticModelRegistryService,
)
from src.app.services.providers.provider_service import ProviderService
from tests.fakes.provider_connection_service import (
    FakeProviderConnectionService,
)
from tests.fakes.provider_repository import FakeProviderRepository
from tests.fakes.secret_service import FakeSecretService


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
def composition_repository() -> FakeCompositionRepository:
    return FakeCompositionRepository()


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
            WorkspaceMembership(
                user_id="user-1",
                workspace_id="workspace-1",
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
    composition_repository: FakeCompositionRepository,
) -> ValidationService:
    repository = FakeValidationRepository(
        instruction_repository=instruction_repository,
        composition_repository=composition_repository,
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
def instruction_service(
    instruction_repository: FakeInstructionRepository,
    validation_service: ValidationService,
    dependency_checker: FakeDependencyChecker,
) -> InstructionService:
    identifier_counter = count(1)

    def create_identifier() -> str:
        return f"instruction-{next(identifier_counter)}"

    clock: Callable[[], datetime] = IncrementingClock()

    return InstructionService(
        repository=instruction_repository,
        validation_service=validation_service,
        dependency_checker=dependency_checker,
        id_factory=create_identifier,
        clock=clock,
    )


@pytest.fixture
def composition_service(
    composition_repository: FakeCompositionRepository,
    validation_service: ValidationService,
    dependency_checker: FakeDependencyChecker,
) -> CompositionService:
    identifier_counter = count(1)

    def create_identifier() -> str:
        return f"composition-{next(identifier_counter)}"

    clock: Callable[[], datetime] = IncrementingClock()

    return CompositionService(
        repository=composition_repository,
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
        provider_state_repository=provider_state_repository,
    )


@pytest.fixture
def model_catalog_service(
    tenant_service: TenantService,
    model_availability_service: ModelAvailabilityService,
) -> ModelCatalogService:
    return ModelCatalogService(
        tenant_service=tenant_service,
        availability_service=model_availability_service,
    )


@pytest.fixture
def model_controller(
    model_catalog_service: ModelCatalogService,
) -> ModelController:
    return ModelController(
        model_catalog_service=model_catalog_service,
    )


@pytest.fixture
def provider_repository() -> FakeProviderRepository:
    return FakeProviderRepository()


@pytest.fixture
def provider_secret_service() -> FakeSecretService:
    return FakeSecretService()


@pytest.fixture
def provider_connection_service() -> FakeProviderConnectionService:
    return FakeProviderConnectionService()


@pytest.fixture
def provider_service(
    provider_repository: FakeProviderRepository,
    tenant_service: TenantService,
    provider_secret_service: FakeSecretService,
    provider_connection_service: FakeProviderConnectionService,
) -> ProviderService:
    identifier_counter = count(1)

    def create_identifier() -> str:
        return f"provider-credential-{next(identifier_counter)}"

    clock: Callable[[], datetime] = IncrementingClock()

    return ProviderService(
        repository=provider_repository,
        tenant_service=tenant_service,
        secret_service=provider_secret_service,
        connection_service=provider_connection_service,
        model_registry=StaticModelRegistryService(
            counts={
                "anthropic": 4,
                "nvidia": 0,
                "ollama": 0,
                "openai": 3,
                "together": 10,
            }
        ),
        id_factory=create_identifier,
        clock=clock,
    )


@pytest.fixture
def provider_controller(
    provider_service: ProviderService,
) -> ProviderController:
    return ProviderController(
        provider_service=provider_service,
    )
