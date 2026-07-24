"""FastAPI dependencies for request context and controllers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, TypeVar

from fastapi import Header, HTTPException, Request, status

from src.app.controllers.loop import LoopController
from src.app.controllers.model import ModelController
from src.app.controllers.persona import PersonaController
from src.app.controllers.skill import SkillController
from src.app.controllers.provider import ProviderController
from src.app.services.execution_instruction_library import (
    ExecutionInstructionLibraryService,
)


ControllerType = TypeVar("ControllerType")


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Authenticated user and optional workspace selection."""

    user_id: str
    requested_workspace_id: str | None = None


async def get_request_context(
    request: Request,
    workspace_id: Annotated[
        str | None,
        Header(
            alias="X-Workspace-ID",
            description="Workspace selected for the request.",
        ),
    ] = None,
) -> RequestContext:
    """
    Build the context shared by every authenticated API endpoint.

    Authentication middleware must set request.state.user_id.
    """

    user_id = getattr(request.state, "user_id", None)

    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "authentication_required",
                "message": "Authentication is required.",
            },
        )

    normalized_workspace_id = None

    if workspace_id is not None:
        normalized_workspace_id = workspace_id.strip() or None

    return RequestContext(
        user_id=user_id.strip(),
        requested_workspace_id=normalized_workspace_id,
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


def get_loop_controller(
    request: Request,
) -> LoopController:
    """Return the configured loop controller."""

    return _get_controller(
        request,
        attribute_name="loop_controller",
        expected_type=LoopController,
    )


def get_model_controller(
    request: Request,
) -> ModelController:
    """Return the configured model controller."""

    return _get_controller(
        request,
        attribute_name="model_controller",
        expected_type=ModelController,
    )


def get_provider_controller(
    request: Request,
) -> ProviderController:
    """Return the configured provider controller."""

    return _get_controller(
        request,
        attribute_name="provider_controller",
        expected_type=ProviderController,
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
