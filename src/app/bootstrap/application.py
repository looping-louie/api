"""Application composition root."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from src.app.bootstrap.pipeline import build_pipeline_controller
from src.app.controllers.activity import ActivityController
from src.app.controllers.activity_run import ActivityRunController
from src.app.controllers.catalog import CatalogController
from src.app.catalogs.persona_skills.loader import (
    PersonaSkillCatalog,
    load_persona_skill_catalog,
)
from src.app.catalogs.providers import PROVIDER_CATALOG
from src.app.controllers.model import ModelController
from src.app.controllers.persona import PersonaController
from src.app.controllers.linked_services import LinkedServiceController
from src.app.controllers.workspace import WorkspaceController
from src.app.controllers.skill import SkillController
from src.app.controllers.worker import WorkerController
from src.app.repositories.activities.sqlite_repository import (
    SqliteActivityRepository,
)
from src.app.repositories.activity_runs.sqlite_repository import (
    SqliteActivityRunRepository,
)
from src.app.repositories.shared.dependency_repository import (
    SqliteDependencyRepository,
)
from src.app.repositories.instructions.repository import (
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
from src.app.repositories.linked_services import SqliteLinkedServiceRepository
from src.app.repositories.workers import SqliteWorkerRepository
from src.app.repositories.workspaces import SqliteWorkspaceRepository
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
from src.app.services.shared.settings import (
    AppSettings,
    get_app_settings,
)
from src.app.services.execution_instructions import (
    ExecutionInstructionLibraryService,
)
from src.app.services.persona_skills.synchronization import (
    CatalogChecksumPolicy,
    PersonaSkillCatalogSynchronizer,
)
from src.app.services.activities.service import ActivityService
from src.app.services.catalogs import StaticCatalogService
from src.app.services.activity_runs import ActivityRunService
from src.app.services.models.availability import ModelAvailabilityService
from src.app.services.models.catalog import ModelCatalogService
from src.app.services.model_execution import ModelExecutionService
from src.app.services.personas import PersonaService
from src.app.services.providers.connection import (
    HttpProviderConnectionService,
)
from src.app.services.linked_services import LinkedServiceService
from src.app.services.providers.secret import FernetSecretService
from src.app.services.shared.dependency_checker import DependencyChecker
from src.app.services.shared.generation import create_identifier, utc_now
from src.app.services.persona_skills import (
    PersonaDefinitionService,
    SkillDefinitionService,
)
from src.app.services.shared.reference_resolver import ReferenceResolver
from src.app.services.shared.tenant import TenantService
from src.app.services.shared.validation import ValidationService
from src.app.services.skills import SkillService
from src.app.services.workers import WorkerService
from src.app.services.workspaces import WorkspaceService


LOGGER = logging.getLogger(__name__)


async def configure_application(
    app: FastAPI,
    *,
    settings: AppSettings | None = None,
    persona_skill_catalog: PersonaSkillCatalog | None = None,
) -> None:
    """Build and register the SQLite application dependencies."""

    resolved_settings = settings or get_app_settings()

    await run_sqlite_migrations(
        database_path=resolved_settings.database_path,
    )

    resolved_catalog = (
        persona_skill_catalog
        if persona_skill_catalog is not None
        else load_persona_skill_catalog()
    )
    catalog_synchronizer = PersonaSkillCatalogSynchronizer(
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
        "Persona and Skill catalog synchronized: inserted=%d updated=%d "
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
    activity_repository = SqliteActivityRepository(
        resolved_settings.database_path,
    )
    activity_run_repository = SqliteActivityRunRepository(
        resolved_settings.database_path,
    )
    linked_service_repository = SqliteLinkedServiceRepository(database)
    worker_repository = SqliteWorkerRepository(database)
    workspace_repository = SqliteWorkspaceRepository(database)

    validation_repository = SqliteValidationRepository(
        resolved_settings.database_path,
    )
    dependency_repository = SqliteDependencyRepository(
        resolved_settings.database_path,
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
        linked_service_repository=linked_service_repository,
    )
    model_catalog_service = ModelCatalogService(
        tenant_service=tenant_service,
        availability_service=model_availability_service,
    )
    catalog_controller = CatalogController(
        static_catalog_service=StaticCatalogService(),
    )

    reference_repository = CompositeReferenceRepository(
        instruction_repository=instruction_repository,
        model_catalog_service=model_catalog_service,
    )
    reference_resolver = ReferenceResolver(
        repository=reference_repository,
    )

    persona_definition_service = PersonaDefinitionService(
        repository=instruction_repository,
        validation_service=validation_service,
        dependency_checker=dependency_checker,
        id_factory=create_identifier,
        clock=utc_now,
    )
    skill_definition_service = SkillDefinitionService(
        repository=instruction_repository,
        validation_service=validation_service,
        dependency_checker=dependency_checker,
        id_factory=create_identifier,
        clock=utc_now,
    )
    secret_service = FernetSecretService(encryption_key)
    linked_service_service = LinkedServiceService(
        repository=linked_service_repository,
        tenant_service=tenant_service,
        secret_service=secret_service,
        connection_service=HttpProviderConnectionService(),
        catalog=PROVIDER_CATALOG,
        dependency_checker=dependency_checker,
        id_factory=create_identifier,
        clock=utc_now,
    )
    workspace_service = WorkspaceService(
        repository=workspace_repository,
        tenant_service=tenant_service,
        linked_service_service=linked_service_service,
        clock=utc_now,
    )
    persona_service = PersonaService(
        tenant_service=tenant_service,
        persona_definition_service=persona_definition_service,
        skill_definition_service=skill_definition_service,
        persona_skill_repository=persona_skill_repository,
    )
    skill_service = SkillService(
        tenant_service=tenant_service,
        skill_definition_service=skill_definition_service,
    )
    activity_service = ActivityService(
        repository=activity_repository,
        tenant_service=tenant_service,
        reference_resolver=reference_resolver,
        id_factory=create_identifier,
        clock=utc_now,
        linked_service_service=linked_service_service,
    )
    activity_run_service = ActivityRunService(
        repository=activity_run_repository,
        activity_service=activity_service,
        tenant_service=tenant_service,
        id_factory=create_identifier,
        clock=utc_now,
        model_execution_service=ModelExecutionService(
            model_catalog_service=model_catalog_service,
            secret_service=secret_service,
            linked_service_repository=linked_service_repository,
        ),
        instruction_library_service=execution_instruction_library_service,
    )
    worker_service = WorkerService(
        repository=worker_repository,
        tenant_service=tenant_service,
        id_factory=create_identifier,
        clock=utc_now,
    )
    app.state.persona_controller = PersonaController(
        persona_service=persona_service,
    )
    app.state.skill_controller = SkillController(
        skill_service=skill_service,
    )
    app.state.activity_controller = ActivityController(
        activity_service=activity_service,
    )
    app.state.activity_run_controller = ActivityRunController(
        activity_run_service=activity_run_service,
    )
    app.state.pipeline_controller = build_pipeline_controller(
        database_path=resolved_settings.database_path,
        tenant_service=tenant_service,
        id_factory=create_identifier,
        clock=utc_now,
        activity_run_repository=activity_run_repository,
        worker_service=worker_service,
        linked_service_service=linked_service_service,
        workspace_service=workspace_service,
    )
    app.state.model_controller = ModelController(
        model_catalog_service=model_catalog_service,
    )
    app.state.catalog_controller = catalog_controller
    app.state.linked_service_controller = LinkedServiceController(
        linked_service_service=linked_service_service,
    )
    app.state.workspace_controller = WorkspaceController(
        service=workspace_service,
    )
    app.state.worker_controller = WorkerController(worker_service=worker_service)

    app.state.database = database
    app.state.persona_skill_catalog = resolved_catalog
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
