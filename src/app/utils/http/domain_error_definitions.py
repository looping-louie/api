"""Domain exception definitions for stable HTTP responses."""

from fastapi import status

from src.app.services.execution_instruction_library import (
    ExecutionInstructionNotFoundError,
)
from src.app.services.loops.types import (
    ArchivedLoopImmutableError,
    LoopNotFoundError,
    LoopValidationError,
)
from src.app.services.loop_runs.service import (
    LoopRunNotFoundError,
    LoopRunUnavailableError,
)
from src.app.repositories.loop_runs.errors import (
    LoopRunInvalidTransitionError,
    LoopRunTokenConflictError,
)
from src.app.services.models.availability import (
    ModelNotFoundError,
    ModelValidationError,
)
from src.app.services.pipelines.types import (
    InvalidPipelineStepsError,
    PipelineArchivedError,
    PipelineNotFoundError,
    UnsupportedHumanGateTypeError,
    UnsupportedPipelineStepError,
)
from src.app.services.providers.connection import ProviderConnectionError
from src.app.services.providers.errors import (
    ProviderConfigurationError,
    UnknownProviderError,
)
from src.app.services.shared.dependency_checker import (
    DependencyValidationError,
    ResourceInUseError,
)
from src.app.services.shared.instruction import (
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
from src.app.services.shared.tenant import (
    TenantAccessDeniedError,
    TenantNotFoundError,
    TenantSelectionRequiredError,
    TenantValidationError,
)
from src.app.services.shared.validation import (
    DomainValidationError,
    DuplicateResourceError,
    ResourceVersionConflictError,
)
from src.app.services.skills.metadata_validator import SkillValidationError

from .domain_error_details import (
    _duplicate_resource_details,
    _execution_instruction_not_found_details,
    _instruction_access_details,
    _instruction_not_found_details,
    _invalid_instruction_type_details,
    _loop_details,
    _model_not_found_details,
    _provider_configuration_details,
    _referenced_resources_details,
    _resource_in_use_details,
    _unknown_provider_details,
    _validation_details,
    _version_conflict_details,
    _workspace_selection_details,
)
from .error_definition import ErrorDefinition
from .pipeline_error_details import (
    pipeline_details,
    unsupported_gate_details,
    unsupported_step_details,
)


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
    LoopRunNotFoundError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code="loop_run_not_found",
    ),
    LoopRunUnavailableError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code="loop_run_unavailable",
    ),
    LoopRunTokenConflictError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code="loop_run_token_conflict",
    ),
    LoopRunInvalidTransitionError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code="loop_run_invalid_transition",
    ),
    PipelineNotFoundError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code="pipeline_not_found",
        details_builder=pipeline_details,
    ),
    PipelineArchivedError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code="pipeline_archived",
        details_builder=pipeline_details,
    ),
    InvalidPipelineStepsError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="invalid_pipeline_steps",
        details_builder=_validation_details,
    ),
    UnsupportedPipelineStepError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="unsupported_pipeline_step",
        details_builder=unsupported_step_details,
    ),
    UnsupportedHumanGateTypeError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="unsupported_human_gate_type",
        details_builder=unsupported_gate_details,
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
