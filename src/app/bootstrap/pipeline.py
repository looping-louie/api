"""Focused composition helper for pipeline dependencies."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from src.app.controllers.pipelines import PipelineController
from src.app.repositories.pipelines.sqlite_repository import (
    SqlitePipelineRepository,
)
from src.app.repositories.activity_runs.repository import ActivityRunRepository
from src.app.repositories.pipeline_runs.sqlite_repository import SqlitePipelineRunRepository
from src.app.services.pipelines.service import PipelineService
from src.app.services.models import ModelExecutionService
from src.app.services.models.catalog import ModelCatalogService
from src.app.services.execution_instructions import ExecutionInstructionLibraryService
from src.app.services.linked_services import LinkedServiceService
from src.app.services.pipeline_runs import PipelineRunService
from src.app.services.shared.tenant import TenantService
from src.app.services.users import UserService
from src.app.services.worker_instances import WorkerInstanceService
from src.app.services.projects.service import ProjectService


def build_pipeline_controller(
    *,
    database_path: Path,
    tenant_service: TenantService,
    id_factory: Callable[[], str],
    clock: Callable[[], datetime],
    activity_run_repository: ActivityRunRepository,
    worker_instance_service: WorkerInstanceService,
    linked_service_service: LinkedServiceService,
    workspace_service: ProjectService,
    user_service: UserService,
    model_execution_service: ModelExecutionService,
    model_catalog_service: ModelCatalogService,
    instruction_library_service: ExecutionInstructionLibraryService,
) -> PipelineController:
    """Build the pipeline persistence, service, and HTTP layers."""

    repository = SqlitePipelineRepository(database_path)
    service = PipelineService(
        repository=repository,
        tenant_service=tenant_service,
        linked_service_service=linked_service_service,
        id_factory=id_factory,
        clock=clock,
    )
    return PipelineController(
        pipeline_service=service,
        pipeline_run_service=PipelineRunService(
            repository=SqlitePipelineRunRepository(database_path),
            activity_run_repository=activity_run_repository,
            pipeline_service=service,
            tenant_service=tenant_service,
            worker_instance_service=worker_instance_service,
            workspace_service=workspace_service,
            user_service=user_service,
            model_execution_service=model_execution_service,
            model_catalog_service=model_catalog_service,
            instruction_library_service=instruction_library_service,
            id_factory=id_factory,
            clock=clock,
        ),
    )
