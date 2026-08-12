"""Focused composition helper for pipeline dependencies."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from src.app.controllers.pipeline import PipelineController
from src.app.repositories.activities.repository import ActivityRepository
from src.app.repositories.pipelines.sqlite_repository import (
    SqlitePipelineRepository,
)
from src.app.services.pipelines.service import PipelineService
from src.app.services.shared.tenant import TenantService


def build_pipeline_controller(
    *,
    database_path: Path,
    activity_repository: ActivityRepository,
    tenant_service: TenantService,
    id_factory: Callable[[], str],
    clock: Callable[[], datetime],
) -> PipelineController:
    """Build the pipeline persistence, service, and HTTP layers."""

    repository = SqlitePipelineRepository(database_path)
    service = PipelineService(
        repository=repository,
        activity_repository=activity_repository,
        tenant_service=tenant_service,
        id_factory=id_factory,
        clock=clock,
    )
    return PipelineController(pipeline_service=service)
