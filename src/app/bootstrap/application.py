"""Application composition root."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from src.app.bootstrap.pipeline import build_pipeline_controller
from src.app.controllers.activities import ActivityController
from src.app.controllers.activity_runs import ActivityRunController
from src.app.controllers.catalogs import CatalogController
from src.app.catalogs.persona_skills.loader import (
    PersonaSkillCatalog,
    load_persona_skill_catalog,
)
from src.app.catalogs.providers import PROVIDER_CATALOG
from src.app.controllers.personas import PersonaController
from src.app.controllers.linked_services import LinkedServiceController
from src.app.controllers.projects import ProjectController
from src.app.controllers.users import UserController
from src.app.controllers.skills import SkillController
from src.app.controllers.workers import WorkerController
from src.app.controllers.worker_instances import WorkerInstanceController
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
    SqliteUserPersonaRepository,
    SqliteUserSkillRepository,
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
from src.app.repositories.worker_instances import SqliteWorkerInstanceRepository
from src.app.repositories.projects import SqliteProjectRepository
from src.app.repositories.pipeline_runs.sqlite_repository import (
    SqlitePipelineRunRepository,
)
from src.app.repositories.users import SqliteUserRepository
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
from src.app.services.models import ModelExecutionService
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
from src.app.services.worker_instances import WorkerInstanceService
from src.app.services.projects.service import ProjectService
from src.app.services.users import UserService


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
        project_id='local-project',
        project_name='Local project',
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
    user_skill_repository = SqliteUserSkillRepository(
        resolved_settings.database_path,
    )
    user_persona_repository = SqliteUserPersonaRepository(
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
    worker_instance_repository = SqliteWorkerInstanceRepository(database)
    pipeline_run_repository = SqlitePipelineRunRepository(
        resolved_settings.database_path,
    )
    project_repository = SqliteProjectRepository(database)
    user_repository = SqliteUserRepository(database)
    user_service = UserService(
        repository=user_repository,
        clock=utc_now,
    )

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
            repository=user_skill_repository,
            persona_repository=user_persona_repository,
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
        user_service=user_service,
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
        repository=user_persona_repository,
        validation_service=validation_service,
        dependency_checker=dependency_checker,
        id_factory=create_identifier,
        clock=utc_now,
    )
    skill_definition_service = SkillDefinitionService(
        repository=user_skill_repository,
        validation_service=validation_service,
        dependency_checker=dependency_checker,
        id_factory=create_identifier,
        clock=utc_now,
    )
    secret_service = FernetSecretService(encryption_key)
    linked_service_service = LinkedServiceService(
        repository=linked_service_repository,
        user_service=user_service,
        tenant_service=tenant_service,
        secret_service=secret_service,
        connection_service=HttpProviderConnectionService(),
        catalog=PROVIDER_CATALOG,
        dependency_checker=dependency_checker,
        id_factory=create_identifier,
        clock=utc_now,
    )
    project_service = ProjectService(
        repository=project_repository,
        tenant_service=tenant_service,
        linked_service_service=linked_service_service,
        user_service=user_service,
        id_factory=create_identifier,
        clock=utc_now,
    )
    persona_service = PersonaService(
        user_service=user_service,
        persona_definition_service=persona_definition_service,
        skill_definition_service=skill_definition_service,
        persona_skill_repository=persona_skill_repository,
    )
    skill_service = SkillService(
        user_service=user_service,
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
    model_execution_service = ModelExecutionService(
        model_catalog_service=model_catalog_service,
        secret_service=secret_service,
        linked_service_repository=linked_service_repository,
        user_service=user_service,
    )
    activity_run_service = ActivityRunService(
        repository=activity_run_repository,
        activity_service=activity_service,
        tenant_service=tenant_service,
        id_factory=create_identifier,
        clock=utc_now,
        model_execution_service=model_execution_service,
        instruction_library_service=execution_instruction_library_service,
        workspace_service=project_service,
        user_service=user_service,
    )
    worker_service = WorkerService(
        repository=worker_repository,
        tenant_service=tenant_service,
        id_factory=create_identifier,
        clock=utc_now,
    )
    worker_instance_service = WorkerInstanceService(
        repository=worker_instance_repository,
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
        worker_instance_service=worker_instance_service,
        linked_service_service=linked_service_service,
        workspace_service=project_service,
        user_service=user_service,
        model_execution_service=model_execution_service,
        model_catalog_service=model_catalog_service,
        instruction_library_service=execution_instruction_library_service,
    )
    app.state.catalog_controller = catalog_controller
    app.state.linked_service_controller = LinkedServiceController(
        linked_service_service=linked_service_service,
    )
    app.state.project_controller = ProjectController(
        service=project_service,
    )
    app.state.user_controller = UserController(
        service=user_service,
        model_catalog_service=model_catalog_service,
    )
    app.state.worker_controller = WorkerController(worker_service=worker_service)
    app.state.worker_instance_controller = WorkerInstanceController(
        service=worker_instance_service,
        pipeline_run_repository=pipeline_run_repository,
        clock=utc_now,
    )

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
