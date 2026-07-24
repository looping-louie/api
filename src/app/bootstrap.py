"""Application composition root."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from src.app.bootstrap_pipeline import build_pipeline_controller
from src.app.catalogs.loader import (
    InstructionCatalog,
    load_instruction_catalog,
)
from src.app.catalogs.providers import PROVIDER_CATALOG
from src.app.controllers.loop import LoopController
from src.app.controllers.model import ModelController
from src.app.controllers.persona import PersonaController
from src.app.controllers.provider import ProviderController
from src.app.controllers.skill import SkillController
from src.app.repositories.loops.sqlite_loop_repository import (
    SqliteLoopRepository,
)
from src.app.repositories.shared.dependency_repository import (
    SqliteDependencyRepository,
)
from src.app.repositories.instructions.instruction_repository import (
    SqliteInstructionRepository,
)
from src.app.repositories.instructions.persona_skill_repository import (
    SqlitePersonaSkillRepository,
)
from src.app.repositories.infrastructure.migration_runner import (
    run_sqlite_migrations,
)
from src.app.repositories.infrastructure.local_tenant_seed import (
    ensure_local_tenant,
)
from src.app.repositories.providers.provider_repository import (
    SqliteProviderRepository,
)
from src.app.repositories.providers.provider_state_repository import (
    ProviderStateRepositoryAdapter,
)
from src.app.repositories.shared.reference_repository import (
    CompositeReferenceRepository,
)
from src.app.repositories.infrastructure.sqlite_database import SqliteDatabase
from src.app.repositories.shared.tenant_repository import (
    SqliteTenantRepository,
)
from src.app.repositories.shared.validation_repository import (
    SqliteValidationRepository,
)
from src.app.services.app_settings_service import (
    AppSettings,
    get_app_settings,
)
from src.app.services.execution_instruction_library import (
    ExecutionInstructionLibraryService,
)
from src.app.services.instruction_catalog_synchronizer import (
    CatalogChecksumPolicy,
    InstructionCatalogSynchronizer,
)
from src.app.services.loop_catalog_seeder import seed_loop_catalog
from src.app.services.loop_service import LoopService
from src.app.services.model_service import (
    ModelAvailabilityService,
    ModelCatalogService,
)
from src.app.services.persona_service import PersonaService
from src.app.services.providers.model_registry_service import (
    CatalogModelRegistryService,
)
from src.app.services.providers.provider_connection_service import (
    HttpProviderConnectionService,
)
from src.app.services.providers.provider_service import ProviderService
from src.app.services.providers.secret_service import FernetSecretService
from src.app.services.shared.dependency_checker import DependencyChecker
from src.app.services.shared.generation import create_identifier, utc_now
from src.app.services.shared.instruction_service import InstructionService
from src.app.services.shared.reference_resolver import ReferenceResolver
from src.app.services.shared.tenant_service import TenantService
from src.app.services.shared.validation_service import ValidationService
from src.app.services.skill_service import SkillService


LOGGER = logging.getLogger(__name__)


async def configure_application(
    app: FastAPI,
    *,
    settings: AppSettings | None = None,
    instruction_catalog: InstructionCatalog | None = None,
) -> None:
    """Build and register the SQLite application dependencies."""

    resolved_settings = settings or get_app_settings()

    await run_sqlite_migrations(
        database_path=resolved_settings.database_path,
    )

    resolved_catalog = (
        instruction_catalog
        if instruction_catalog is not None
        else load_instruction_catalog()
    )
    catalog_synchronizer = InstructionCatalogSynchronizer(
        database_path=resolved_settings.database_path,
        checksum_policy=(
            CatalogChecksumPolicy.REQUIRE_VERSION_INCREMENT
            if getattr(
                resolved_settings,
                "catalog_strict_versioning",
                False,
            )
            else CatalogChecksumPolicy.ALLOW_WITH_WARNING
        ),
    )
    catalog_synchronization = catalog_synchronizer.synchronize(
        resolved_catalog,
    )
    LOGGER.info(
        "Instruction catalog synchronized: inserted=%d updated=%d "
        "unchanged=%d deprecated=%d",
        catalog_synchronization.inserted,
        catalog_synchronization.updated,
        catalog_synchronization.unchanged,
        catalog_synchronization.deprecated,
    )

    await ensure_local_tenant(
        database_path=resolved_settings.database_path,
        workspace_id="local-workspace",
        workspace_name="Local workspace",
        user_id="local-user",
    )
    installed_loops = await seed_loop_catalog(
        database_path=resolved_settings.database_path,
    )
    LOGGER.info(
        "Loop catalog installed: inserted=%d",
        installed_loops,
    )

    encryption_key = _require_encryption_key(
        resolved_settings,
    )

    database = SqliteDatabase(
        resolved_settings.database_path,
    )

    tenant_repository = SqliteTenantRepository(
        resolved_settings.database_path,
    )
    instruction_repository = SqliteInstructionRepository(
        resolved_settings.database_path,
    )
    persona_skill_repository = SqlitePersonaSkillRepository(
        resolved_settings.database_path,
    )
    loop_repository = SqliteLoopRepository(
        resolved_settings.database_path,
    )
    provider_repository = SqliteProviderRepository(
        database,
    )

    validation_repository = SqliteValidationRepository(
        resolved_settings.database_path,
    )
    dependency_repository = SqliteDependencyRepository(
        resolved_settings.database_path,
    )
    provider_state_repository = ProviderStateRepositoryAdapter(
        provider_repository=provider_repository,
        catalog=PROVIDER_CATALOG,
    )

    tenant_service = TenantService(
        repository=tenant_repository,
    )
    execution_instruction_library_service = (
        ExecutionInstructionLibraryService(
            repository=instruction_repository,
            persona_skill_repository=persona_skill_repository,
            tenant_service=tenant_service,
        )
    )
    validation_service = ValidationService(
        repository=validation_repository,
    )
    dependency_checker = DependencyChecker(
        repository=dependency_repository,
    )

    model_availability_service = ModelAvailabilityService(
        provider_state_repository=provider_state_repository,
    )
    model_catalog_service = ModelCatalogService(
        tenant_service=tenant_service,
        availability_service=model_availability_service,
    )

    reference_repository = CompositeReferenceRepository(
        instruction_repository=instruction_repository,
        model_catalog_service=model_catalog_service,
    )
    reference_resolver = ReferenceResolver(
        repository=reference_repository,
    )

    instruction_service = InstructionService(
        repository=instruction_repository,
        validation_service=validation_service,
        dependency_checker=dependency_checker,
        id_factory=create_identifier,
        clock=utc_now,
    )
    persona_service = PersonaService(
        tenant_service=tenant_service,
        instruction_service=instruction_service,
        persona_skill_repository=persona_skill_repository,
    )
    skill_service = SkillService(
        tenant_service=tenant_service,
        instruction_service=instruction_service,
    )
    loop_service = LoopService(
        repository=loop_repository,
        tenant_service=tenant_service,
        reference_resolver=reference_resolver,
        dependency_checker=dependency_checker,
        id_factory=create_identifier,
        clock=utc_now,
    )
    provider_service = ProviderService(
        repository=provider_repository,
        tenant_service=tenant_service,
        secret_service=FernetSecretService(
            encryption_key,
        ),
        connection_service=HttpProviderConnectionService(),
        model_registry=CatalogModelRegistryService(),
        catalog=PROVIDER_CATALOG,
        id_factory=create_identifier,
        clock=utc_now,
    )

    app.state.persona_controller = PersonaController(
        persona_service=persona_service,
    )
    app.state.skill_controller = SkillController(
        skill_service=skill_service,
    )
    app.state.loop_controller = LoopController(
        loop_service=loop_service,
    )
    app.state.pipeline_controller = build_pipeline_controller(
        database_path=resolved_settings.database_path,
        loop_repository=loop_repository,
        tenant_service=tenant_service,
        id_factory=create_identifier,
        clock=utc_now,
    )
    app.state.model_controller = ModelController(
        model_catalog_service=model_catalog_service,
    )
    app.state.provider_controller = ProviderController(
        provider_service=provider_service,
    )

    app.state.database = database
    app.state.instruction_catalog = resolved_catalog
    app.state.catalog_synchronization = catalog_synchronization
    app.state.execution_instruction_library_service = (
        execution_instruction_library_service
    )


def _require_encryption_key(
    settings: AppSettings,
) -> str:
    """Return the provider encryption key or fail securely."""

    if settings.encryption_key is None:
        raise RuntimeError(
            "LOUIE_ENCRYPTION_KEY is required to configure providers."
        )

    return settings.encryption_key
