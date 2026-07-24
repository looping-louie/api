"""Translate domain exceptions into stable HTTP error responses."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.app.services.execution_instruction_library import (
    ExecutionInstructionNotFoundError,
)
from src.app.services.loop_types import (
    ArchivedLoopImmutableError,
    LoopNotFoundError,
    LoopValidationError,
)
from src.app.services.shared.dependency_checker import (
    DependencyValidationError,
    ResourceInUseError,
)
from src.app.services.shared.instruction_service import (
    BuiltinInstructionImmutableError,
    InstructionDisabledError,
    InstructionNotFoundError,
    InstructionNotOwnedError,
    InstructionValidationError,
    InstructionVersionConflictError,
    InvalidInstructionTypeError,
)
from src.app.services.shared.reference_resolver import (
    ReferenceValidationError,
    ResourceNotFoundError,
)
from src.app.services.shared.tenant_service import (
    TenantAccessDeniedError,
    TenantNotFoundError,
    TenantSelectionRequiredError,
    TenantValidationError,
)
from src.app.services.shared.validation_service import (
    DomainValidationError,
    DuplicateResourceError,
    ResourceVersionConflictError,
)
from src.app.services.skill_metadata_validator import SkillValidationError
from src.app.services.model_service import (
    ModelNotFoundError,
    ModelValidationError,
)
from src.app.services.providers.provider_connection_service import (
    ProviderConnectionError,
)
from src.app.services.providers.provider_errors import (
    ProviderConfigurationError,
    UnknownProviderError,
)


ErrorDetails = dict[str, Any]
DetailsBuilder = Callable[[Exception], ErrorDetails | None]


@dataclass(frozen=True, slots=True)
class ErrorDefinition:
    """HTTP representation of a domain exception."""

    status_code: int
    code: str
    public_message: str | None = None
    details_builder: DetailsBuilder | None = None


def _unknown_provider_details(error: Exception) -> ErrorDetails:
    """Return the unknown provider identity."""

    assert isinstance(error, UnknownProviderError)

    return {
        "resource_type": "provider",
        "resource_id": error.provider_id,
    }


def _provider_configuration_details(
    error: Exception,
) -> ErrorDetails:
    """Return invalid provider configuration details."""

    assert isinstance(error, ProviderConfigurationError)

    return {
        "provider_id": error.provider_id,
        "reason": error.reason,
    }


def _model_not_found_details(error: Exception) -> ErrorDetails:
    """Return the missing model identity."""

    assert isinstance(error, ModelNotFoundError)

    return {
        "resource_type": "model",
        "resource_id": error.model_id,
    }


def _validation_details(error: Exception) -> ErrorDetails:
    """Return field-oriented validation details."""

    return {
        "field": getattr(error, "field_name", None),
        "reason": getattr(error, "message", str(error)),
    }


def _instruction_not_found_details(error: Exception) -> ErrorDetails:
    """Return the missing instruction identity."""

    assert isinstance(error, InstructionNotFoundError)

    return {
        "resource_type": error.instruction_type,
        "resource_id": error.instruction_id,
    }


def _instruction_access_details(error: Exception) -> ErrorDetails:
    """Return the instruction rejected by an access rule."""

    return {
        "resource_type": getattr(error, "instruction_type"),
        "resource_id": getattr(error, "instruction_id"),
    }


def _execution_instruction_not_found_details(
    error: Exception,
) -> ErrorDetails:
    """Return the missing execution instruction identity."""

    assert isinstance(error, ExecutionInstructionNotFoundError)

    return {
        "resource_type": error.instruction_type,
        "resource_id": error.instruction_id,
    }


def _loop_details(error: Exception) -> ErrorDetails:
    """Return the loop identity carried by loop-specific errors."""

    return {
        "resource_type": "loop",
        "resource_id": getattr(error, "loop_id"),
    }


def _referenced_resources_details(error: Exception) -> ErrorDetails:
    """Return every unresolved resource reference."""

    assert isinstance(error, ResourceNotFoundError)

    return {
        "references": [
            {
                "resource_type": reference.resource_type,
                "resource_id": reference.resource_id,
            }
            for reference in error.references
        ],
    }


def _duplicate_resource_details(error: Exception) -> ErrorDetails:
    """Return the conflicting resource name and identity."""

    assert isinstance(error, DuplicateResourceError)

    return {
        "resource_type": error.resource_type,
        "name": error.name,
        "existing_resource_id": error.existing_resource_id,
    }


def _version_conflict_details(error: Exception) -> ErrorDetails:
    """Return optimistic-concurrency versions and resource identity."""

    details: ErrorDetails = {
        "expected_version": getattr(error, "expected_version", None),
        "current_version": getattr(error, "current_version", None),
    }

    resource_id = getattr(error, "instruction_id", None)
    resource_type = getattr(error, "instruction_type", None)

    if resource_id is not None:
        details["resource_id"] = resource_id

    if resource_type is not None:
        details["resource_type"] = resource_type

    return details


def _resource_in_use_details(error: Exception) -> ErrorDetails:
    """Return blocking dependency usages."""

    assert isinstance(error, ResourceInUseError)

    return {
        "resource_type": error.target.resource_type,
        "resource_id": error.target.resource_id,
        "usages": [
            {
                "resource_type": usage.source.resource_type,
                "resource_id": usage.source.resource_id,
                "relation": usage.relation,
                "blocking": usage.blocking,
            }
            for usage in error.usages
        ],
    }


def _workspace_selection_details(error: Exception) -> ErrorDetails:
    """Return the workspaces available for explicit selection."""

    assert isinstance(error, TenantSelectionRequiredError)

    return {
        "workspace_ids": list(error.workspace_ids),
    }


def _invalid_instruction_type_details(error: Exception) -> ErrorDetails:
    """Return the unsupported instruction type."""

    assert isinstance(error, InvalidInstructionTypeError)

    return {
        "instruction_type": error.instruction_type,
    }


ERROR_DEFINITIONS: dict[type[Exception], ErrorDefinition] = {
    TenantValidationError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="tenant_validation_error",
        details_builder=_validation_details,
    ),
    TenantNotFoundError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code="workspace_not_found",
        public_message="No accessible workspace was found.",
    ),
    TenantAccessDeniedError: ErrorDefinition(
        status_code=status.HTTP_403_FORBIDDEN,
        code="workspace_access_denied",
        public_message="You do not have access to the requested workspace.",
    ),
    TenantSelectionRequiredError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code="workspace_selection_required",
        public_message="A workspace must be selected for this request.",
        details_builder=_workspace_selection_details,
    ),
    InvalidInstructionTypeError: ErrorDefinition(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="unsupported_instruction_type",
        details_builder=_invalid_instruction_type_details,
    ),
    InstructionNotFoundError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code="instruction_not_found",
        details_builder=_instruction_not_found_details,
    ),
    BuiltinInstructionImmutableError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code="builtin_instruction_immutable",
        details_builder=_instruction_access_details,
    ),
    InstructionDisabledError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code="instruction_disabled",
        details_builder=_instruction_access_details,
    ),
    InstructionNotOwnedError: ErrorDefinition(
        status_code=status.HTTP_403_FORBIDDEN,
        code="instruction_not_owned",
        details_builder=_instruction_access_details,
    ),
    InstructionVersionConflictError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code="version_conflict",
        details_builder=_version_conflict_details,
    ),
    InstructionValidationError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="instruction_validation_error",
        details_builder=_validation_details,
    ),
    LoopNotFoundError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code="loop_not_found",
        details_builder=_loop_details,
    ),
    ReferenceValidationError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="reference_validation_error",
        details_builder=_validation_details,
    ),
    ResourceNotFoundError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code="referenced_resource_not_found",
        details_builder=_referenced_resources_details,
    ),
    ExecutionInstructionNotFoundError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code="execution_instruction_not_found",
        details_builder=_execution_instruction_not_found_details,
    ),
    DependencyValidationError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="dependency_validation_error",
        details_builder=_validation_details,
    ),
    ResourceInUseError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code="resource_in_use",
        details_builder=_resource_in_use_details,
    ),
    DomainValidationError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="validation_error",
        details_builder=_validation_details,
    ),
    DuplicateResourceError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code="duplicate_resource",
        details_builder=_duplicate_resource_details,
    ),
    ResourceVersionConflictError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code="version_conflict",
        details_builder=_version_conflict_details,
    ),
    SkillValidationError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="skill_validation_error",
        details_builder=_validation_details,
    ),
    LoopValidationError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="loop_validation_error",
        details_builder=_validation_details,
    ),
    ArchivedLoopImmutableError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code="archived_loop_immutable",
        details_builder=_loop_details,
    ),
    ModelNotFoundError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code="model_not_found",
        details_builder=_model_not_found_details,
    ),
    ModelValidationError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="model_validation_error",
        details_builder=_validation_details,
    ),
    UnknownProviderError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code="provider_not_found",
        details_builder=_unknown_provider_details,
    ),
    ProviderConfigurationError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="provider_configuration_error",
        details_builder=_provider_configuration_details,
    ),
    ProviderConnectionError: ErrorDefinition(
        status_code=status.HTTP_502_BAD_GATEWAY,
        code="provider_connection_error",
        public_message="The provider connection could not be established.",
    ),
}


async def domain_exception_handler(
    _request: Request,
    error: Exception,
) -> JSONResponse:
    """Convert a known domain exception into a consistent HTTP response."""

    definition = ERROR_DEFINITIONS.get(type(error))

    if definition is None:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred.",
                    "details": None,
                },
            },
        )

    details = None

    if definition.details_builder is not None:
        details = definition.details_builder(error)

    return JSONResponse(
        status_code=definition.status_code,
        content={
            "error": {
                "code": definition.code,
                "message": definition.public_message or str(error),
                "details": details,
            },
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register every domain-to-HTTP exception mapping."""

    for error_type in ERROR_DEFINITIONS:
        app.add_exception_handler(
            error_type,
            domain_exception_handler,
        )
