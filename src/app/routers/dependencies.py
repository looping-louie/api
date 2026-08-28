"""FastAPI dependencies for request context and controllers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, TypeVar

from fastapi import Header, HTTPException, Request, status

from src.app.controllers.activities import ActivityController
from src.app.controllers.activity_runs import ActivityRunController
from src.app.controllers.catalogs import CatalogController
from src.app.controllers.pipelines import PipelineController
from src.app.controllers.personas import PersonaController
from src.app.controllers.skills import SkillController
from src.app.controllers.workers import WorkerController
from src.app.controllers.linked_services import LinkedServiceController
from src.app.controllers.projects import ProjectController
from src.app.controllers.users import UserController
from src.app.services.execution_instructions import (
    ExecutionInstructionLibraryService,
)


ControllerType = TypeVar("ControllerType")


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Authenticated User and optional Project selection."""

    user_id: str
    requested_project_id: str | None = None


async def get_request_context(
    request: Request,
    request_user_id: Annotated[
        str | None,
        Header(
            alias='X-User-ID',
            description='Identity acting on the request.',
        ),
    ] = None,
    requested_project_id_header: Annotated[
        str | None,
        Header(
            alias="X-Project-ID",
            description="Project selected for the request.",
        ),
    ] = None,
) -> RequestContext:
    """
    Build the context shared by every authenticated API endpoint.

    Authentication middleware must set request.state.user_id.
    """

    user_id = getattr(request.state, 'user_id', None)
    if not isinstance(user_id, str) or not user_id.strip():
        user_id = request_user_id

    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "authentication_required",
                "message": "Authentication is required.",
            },
        )

    normalized_project_id = None

    if requested_project_id_header is not None:
        normalized_project_id = requested_project_id_header.strip() or None

    return RequestContext(
        user_id=user_id.strip(),
        requested_project_id=normalized_project_id,
    )


def _get_controller(
    request: Request,
    *,
    attribute_name: str,
    expected_type: type[ControllerType],
) -> ControllerType:
    """Return a configured controller or a service-unavailable response."""

    controller = getattr(
        request.app.state,
        attribute_name,
        None,
    )

    if not isinstance(controller, expected_type):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "service_unavailable",
                "message": (
                    f"{expected_type.__name__} has not been configured."
                ),
            },
        )

    return controller


def get_persona_controller(
    request: Request,
) -> PersonaController:
    """Return the configured persona controller."""

    return _get_controller(
        request,
        attribute_name="persona_controller",
        expected_type=PersonaController,
    )


def get_skill_controller(
    request: Request,
) -> SkillController:
    """Return the configured skill controller."""

    return _get_controller(
        request,
        attribute_name="skill_controller",
        expected_type=SkillController,
    )


def get_activity_controller(
    request: Request,
) -> ActivityController:
    """Return the configured activity controller."""

    return _get_controller(
        request,
        attribute_name='activity_controller',
        expected_type=ActivityController,
    )


def get_activity_run_controller(
    request: Request,
) -> ActivityRunController:
    """Return the configured activity-run controller."""

    return _get_controller(
        request,
        attribute_name='activity_run_controller',
        expected_type=ActivityRunController,
    )


def get_pipeline_controller(
    request: Request,
) -> PipelineController:
    """Return the configured pipeline controller."""

    return _get_controller(
        request,
        attribute_name="pipeline_controller",
        expected_type=PipelineController,
    )


def get_catalog_controller(
    request: Request,
) -> CatalogController:
    """Return the configured controller for static catalogs."""

    return _get_controller(
        request,
        attribute_name='catalog_controller',
        expected_type=CatalogController,
    )


def get_linked_service_controller(
    request: Request,
) -> LinkedServiceController:
    """Return the configured linked-service controller."""

    return _get_controller(
        request,
        attribute_name='linked_service_controller',
        expected_type=LinkedServiceController,
    )


def get_project_controller(
    request: Request,
) -> ProjectController:
    """Return the configured Project controller."""

    return _get_controller(
        request,
        attribute_name='project_controller',
        expected_type=ProjectController,
    )


def get_user_controller(request: Request) -> UserController:
    """Return the configured current-user controller."""

    return _get_controller(
        request,
        attribute_name='user_controller',
        expected_type=UserController,
    )


def get_execution_instruction_library_service(
    request: Request,
) -> ExecutionInstructionLibraryService:
    """Return the configured SQL-backed execution instruction library."""

    return _get_controller(
        request,
        attribute_name="execution_instruction_library_service",
        expected_type=ExecutionInstructionLibraryService,
    )


def get_worker_controller(request: Request) -> WorkerController:
    """Return the configured runtime worker registration controller."""

    return _get_controller(
        request,
        attribute_name='worker_controller',
        expected_type=WorkerController,
    )
