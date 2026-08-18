"""Structured details exposed for known domain errors."""

from src.app.services.execution_instructions import (
    ExecutionInstructionNotFoundError,
)
from src.app.services.models.availability import ModelNotFoundError
from src.app.services.providers.errors import (
    ProviderConfigurationError,
    UnknownProviderError,
)
from src.app.services.linked_services import LinkedServiceNotFoundError
from src.app.services.shared.dependency_checker import ResourceInUseError
from src.app.services.instructions import (
    InstructionNotFoundError,
    InvalidInstructionTypeError,
)
from src.app.services.shared.reference_resolver import ResourceNotFoundError
from src.app.services.shared.tenant import TenantSelectionRequiredError
from src.app.services.shared.validation import DuplicateResourceError

from .error_definition import ErrorDetails


def _unknown_provider_details(error: Exception) -> ErrorDetails:
    """Return the unknown provider identity."""

    assert isinstance(error, UnknownProviderError)

    return {
        "resource_type": "provider",
        "resource_id": error.provider_id,
    }


def _linked_service_not_found_details(error: Exception) -> ErrorDetails:
    """Return the missing linked-service identity."""

    assert isinstance(error, LinkedServiceNotFoundError)

    return {
        'resource_type': 'linked_service',
        'resource_id': error.service_id,
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
