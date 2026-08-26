"""Domain exception definitions for stable HTTP responses."""

from fastapi import status

from src.app.services.activities.service import (
    ActivityNotFoundError,
    ActivityValidationError,
)
from src.app.repositories.activity_runs.errors import (
    ActivityRunInvalidTransitionError,
    ActivityRunTokenConflictError,
)
from src.app.services.activity_runs.types import (
    ActivityRunNotFoundError,
    ActivityRunUnavailableError,
    ActivityRunValidationError,
)
from src.app.services.execution_instructions import (
    ExecutionInstructionNotFoundError,
)
from src.app.services.models.availability import (
    ModelNotFoundError,
    ModelValidationError,
)
from src.app.services.models import (
    ModelExecutionError,
    ModelOutputValidationError,
)
from src.app.services.pipelines.types import (
    InvalidPipelineStepsError,
    PipelineArchivedError,
    PipelineNotFoundError,
)
from src.app.services.pipeline_runs import (
    PipelineRunNotFoundError,
    PipelineRunPreconditionFailedError,
    PipelineRunUnavailableError,
)
from src.app.services.providers.connection import ProviderConnectionError
from src.app.services.providers.errors import (
    ProviderConfigurationError,
    UnknownProviderError,
)
from src.app.services.linked_services import (
    LinkedServiceNameConflictError,
    LinkedServiceNotFoundError,
    LinkedServiceSelectionUnavailableError,
)
from src.app.services.shared.dependency_checker import (
    DependencyValidationError,
    ResourceInUseError,
)
from src.app.services.persona_skills import (
    BuiltinDefinitionImmutableError,
    DefinitionDisabledError,
    DefinitionNotFoundError,
    DefinitionNotOwnedError,
    DefinitionValidationError,
    DefinitionVersionConflictError,
    InvalidDefinitionTypeError,
)
from src.app.services.shared.reference_resolver import (
    ReferenceValidationError,
    ResourceNotFoundError,
)
from src.app.services.workers import (
    WorkerHarnessUnavailableError,
    WorkerNotFoundError,
    WorkerUnavailableError,
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
from src.app.services.skills import SkillValidationError
from src.app.services.users import UserNotFoundError

from .domain_error_details import (
    _duplicate_resource_details,
    _execution_instruction_not_found_details,
    _instruction_access_details,
    _instruction_not_found_details,
    _invalid_instruction_type_details,
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
from .domain_error_details import _linked_service_not_found_details


ERROR_DEFINITIONS: dict[type[Exception], ErrorDefinition] = {
    UserNotFoundError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code='user_not_found',
    ),
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
    InvalidDefinitionTypeError: ErrorDefinition(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="unsupported_instruction_type",
        details_builder=_invalid_instruction_type_details,
    ),
    DefinitionNotFoundError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code="instruction_not_found",
        details_builder=_instruction_not_found_details,
    ),
    BuiltinDefinitionImmutableError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code="builtin_instruction_immutable",
        details_builder=_instruction_access_details,
    ),
    DefinitionDisabledError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code="instruction_disabled",
        details_builder=_instruction_access_details,
    ),
    DefinitionNotOwnedError: ErrorDefinition(
        status_code=status.HTTP_403_FORBIDDEN,
        code="instruction_not_owned",
        details_builder=_instruction_access_details,
    ),
    DefinitionVersionConflictError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code="version_conflict",
        details_builder=_version_conflict_details,
    ),
    DefinitionValidationError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="instruction_validation_error",
        details_builder=_validation_details,
    ),
    ActivityNotFoundError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code='activity_not_found',
    ),
    ActivityRunUnavailableError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code='activity_run_unavailable',
    ),
    ActivityRunNotFoundError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code='activity_run_not_found',
    ),
    ActivityRunTokenConflictError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code='activity_run_token_conflict',
    ),
    ActivityRunInvalidTransitionError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code='activity_run_invalid_transition',
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
    PipelineRunNotFoundError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code='pipeline_run_not_found',
    ),
    PipelineRunPreconditionFailedError: ErrorDefinition(
        status_code=status.HTTP_412_PRECONDITION_FAILED,
        code='pipeline_run_precondition_failed',
    ),
    PipelineRunUnavailableError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code='pipeline_run_unavailable',
    ),
    WorkerNotFoundError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code='worker_not_found',
    ),
    WorkerUnavailableError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code='worker_unavailable',
    ),
    WorkerHarnessUnavailableError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code='worker_harness_unavailable',
    ),
    InvalidPipelineStepsError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="invalid_pipeline_steps",
        details_builder=_validation_details,
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
    ActivityValidationError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code='activity_validation_error',
        details_builder=_validation_details,
    ),
    ActivityRunValidationError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code='activity_run_validation_error',
        details_builder=_validation_details,
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
    ModelExecutionError: ErrorDefinition(
        status_code=status.HTTP_502_BAD_GATEWAY,
        code="model_execution_error",
        public_message="The model provider could not complete the request.",
    ),
    ModelOutputValidationError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="model_output_error",
        public_message="The model response did not satisfy the required format.",
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
    LinkedServiceNotFoundError: ErrorDefinition(
        status_code=status.HTTP_404_NOT_FOUND,
        code='linked_service_not_found',
        details_builder=_linked_service_not_found_details,
    ),
    LinkedServiceNameConflictError: ErrorDefinition(
        status_code=status.HTTP_409_CONFLICT,
        code='linked_service_name_conflict',
    ),
    LinkedServiceSelectionUnavailableError: ErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code='linked_service_selection_unavailable',
        details_builder=_validation_details,
    ),
}
