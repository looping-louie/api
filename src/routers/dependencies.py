"""FastAPI dependencies for request context and controllers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, TypeVar

from fastapi import Header, HTTPException, Request, status

from src.controllers.activities import ActivityController
from src.controllers.activity_runs import ActivityRunController
from src.controllers.catalogs import CatalogController
from src.controllers.pipelines import PipelineController
from src.controllers.personas import PersonaController
from src.controllers.skills import SkillController
from src.controllers.worker_instances import WorkerInstanceController
from src.controllers.linked_services import LinkedServiceController
from src.controllers.projects import ProjectController
from src.controllers.users import UserController
from src.controllers.authentication import AuthenticationController
from src.models.service_account import ServiceAccount
from src.services.execution_instructions import (
    ExecutionInstructionLibraryService,
)


ControllerType = TypeVar("ControllerType")


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Authenticated User and optional Project selection."""

    user_id: str
    requested_project_id: str | None = None


@dataclass(frozen=True, slots=True)
class RuntimeRequestContext:
    """Authenticated runtime service account and selected Project."""

    administrator_id: str
    service_account_id: str
    project_id: str


ExecutionRequestContext = RequestContext | RuntimeRequestContext


async def get_request_context(
    request: Request,
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


async def get_runtime_request_context(
    request: Request,
    requested_project_id_header: Annotated[
        str | None,
        Header(alias='X-Project-ID'),
    ] = None,
) -> RuntimeRequestContext:
    """Require a service account bound to the explicitly selected Project."""

    account = getattr(request.state, 'service_account', None)
    if not isinstance(account, ServiceAccount):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                'code': 'runtime_authentication_required',
                'message': 'A runtime service credential is required.',
            },
        )
    project_id = (
        requested_project_id_header.strip()
        if isinstance(requested_project_id_header, str)
        else ''
    )
    if not project_id or project_id not in account.project_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                'code': 'runtime_project_access_denied',
                'message': 'The runtime service credential cannot access this Project.',
            },
        )
    return RuntimeRequestContext(
        administrator_id=account.administrator_id,
        service_account_id=account.id,
        project_id=project_id,
    )


async def get_runtime_or_user_request_context(
    request: Request,
    requested_project_id_header: Annotated[
        str | None,
        Header(alias='X-Project-ID'),
    ] = None,
) -> ExecutionRequestContext:
    """Resolve human identity or a service account on runtime execution paths."""

    user_id = getattr(request.state, 'user_id', None)
    if isinstance(user_id, str) and user_id.strip():
        return RequestContext(
            user_id=user_id.strip(),
            requested_project_id=(
                requested_project_id_header.strip()
                if requested_project_id_header is not None
                else None
            ),
        )
    return await get_runtime_request_context(
        request=request,
        requested_project_id_header=requested_project_id_header,
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


def get_authentication_controller(
    request: Request,
) -> AuthenticationController:
    """Return the configured controller for local account authentication."""

    return _get_controller(
        request,
        attribute_name='authentication_controller',
        expected_type=AuthenticationController,
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


def get_worker_instance_controller(request: Request) -> WorkerInstanceController:
    """Return the configured Worker lifecycle controller."""

    return _get_controller(
        request,
        attribute_name='worker_instance_controller',
        expected_type=WorkerInstanceController,
    )
