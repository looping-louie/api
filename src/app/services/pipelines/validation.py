"""Normalization and validation rules for complete pipelines."""

from __future__ import annotations

from pydantic import ValidationError

from src.app.models.changelog import JsonObject
from src.app.schemas.activity import validate_activity_config
from src.app.models.pipeline import (
    PipelineDocument,
    PipelineHarness,
    PipelineStatus,
    PipelineStep,
)
from src.app.services.pipelines.types import (
    InvalidPipelineStepsError,
    PipelineActivityDependencyInput,
    PipelineActivityInput,
    PipelineHarnessInput,
)


def require_text(value: object, field_name: str) -> str:
    """Return stripped non-empty text."""

    if not isinstance(value, str) or not value.strip():
        raise InvalidPipelineStepsError(
            field_name=field_name,
            message="must be a non-empty string",
        )
    return value.strip()


def normalize_description(value: object) -> str:
    """Return a description after validating its string type."""

    if not isinstance(value, str):
        raise InvalidPipelineStepsError(
            field_name="description",
            message="must be a string",
        )
    return value.strip()


def normalize_status(value: object) -> PipelineStatus:
    """Return one supported persisted pipeline status."""

    if value not in {"active", "disabled", "archived"}:
        raise InvalidPipelineStepsError(
            field_name="status",
            message="must be active, disabled, or archived",
        )
    return value  # type: ignore[return-value]


def normalize_harness(value: object) -> PipelineHarness:
    """Return the currently supported Pipeline Harness selection."""

    if not isinstance(value, PipelineHarnessInput):
        raise InvalidPipelineStepsError(
            field_name='harness',
            message='must select a supported Harness',
        )
    if value.kind != 'louie':
        raise InvalidPipelineStepsError(
            field_name='harness.kind',
            message='must be louie',
        )
    if value.version != 'v1':
        raise InvalidPipelineStepsError(
            field_name='harness.version',
            message='must be v1',
        )
    if value.config:
        raise InvalidPipelineStepsError(
            field_name='harness.config',
            message='must be empty for louie',
        )
    return PipelineHarness()


def normalize_steps(
    values: object,
) -> tuple[PipelineActivityInput, ...]:
    """Validate a complete ordered step collection."""

    if not isinstance(values, (tuple, list)):
        raise InvalidPipelineStepsError(
            field_name="steps",
            message="must be an array",
        )
    if not values:
        raise InvalidPipelineStepsError(
            field_name="steps",
            message="must contain at least one step",
        )

    steps: list[PipelineActivityInput] = []
    for position, value in enumerate(values):
        if not isinstance(value, PipelineActivityInput):
            raise InvalidPipelineStepsError(
                field_name=f"steps.{position}",
                message="must be an activity definition",
            )
        if value.type not in {
            'approval',
            'quiz',
            'direct_loop',
            'refinement_loop',
            'roundtable_loop',
        }:
            raise InvalidPipelineStepsError(
                field_name=f'steps.{position}.type',
                message='must contain a supported activity type',
            )
        try:
            config = validate_activity_config(
                activity_type=value.type,
                value=value.config,
            ).model_dump(by_alias=True)
        except ValidationError as error:
            raise InvalidPipelineStepsError(
                field_name=f'steps.{position}.config',
                message=error.errors()[0]['msg'],
            ) from error
        steps.append(
            PipelineActivityInput(
                name=require_text(value.name, f"steps.{position}.name"),
                description=normalize_description(value.description),
                type=require_text(value.type, f"steps.{position}.type"),
                config=config,
                depends_on=_normalize_dependencies(value.depends_on, position),
            )
        )
    _validate_dependency_graph(steps)
    return tuple(steps)


def _normalize_dependencies(
    values: object,
    position: int,
) -> tuple[PipelineActivityDependencyInput, ...]:
    """Normalize named dependency conditions for one inline Activity."""

    if not isinstance(values, tuple):
        raise InvalidPipelineStepsError(
            field_name=f'steps.{position}.dependsOn',
            message='must be an array',
        )
    dependencies: list[PipelineActivityDependencyInput] = []
    seen_activities: set[str] = set()
    for dependency_position, value in enumerate(values):
        if not isinstance(value, PipelineActivityDependencyInput):
            raise InvalidPipelineStepsError(
                field_name=(
                    f'steps.{position}.dependsOn.{dependency_position}'
                ),
                message='must be an Activity dependency',
            )
        activity = require_text(
            value.activity,
            f'steps.{position}.dependsOn.{dependency_position}.activity',
        )
        if value.condition not in ('success', 'failure'):
            raise InvalidPipelineStepsError(
                field_name=(
                    f'steps.{position}.dependsOn.{dependency_position}.condition'
                ),
                message='must be success or failure',
            )
        if activity in seen_activities:
            raise InvalidPipelineStepsError(
                field_name=f'steps.{position}.dependsOn',
                message='must not contain duplicate dependencies',
            )
        seen_activities.add(activity)
        dependencies.append(
            PipelineActivityDependencyInput(
                activity=activity,
                condition=value.condition,
            )
        )
    return tuple(dependencies)


def _validate_dependency_graph(
    steps: list[PipelineActivityInput],
) -> None:
    """Require unique names and an acyclic graph of named dependencies."""

    positions_by_name: dict[str, list[int]] = {}
    for position, step in enumerate(steps):
        positions_by_name.setdefault(step.name, []).append(position)

    dependencies_by_position: dict[int, tuple[int, ...]] = {}
    for position, step in enumerate(steps):
        dependencies: list[int] = []
        for dependency_position, dependency in enumerate(step.depends_on):
            target_positions = positions_by_name.get(dependency.activity, [])
            if not target_positions:
                raise InvalidPipelineStepsError(
                    field_name=(
                        f'steps.{position}.dependsOn.{dependency_position}.activity'
                    ),
                    message='must reference a step Activity name',
                )
            if len(target_positions) != 1:
                raise InvalidPipelineStepsError(
                    field_name=(
                        f'steps.{position}.dependsOn.{dependency_position}.activity'
                    ),
                    message='must reference a uniquely named step Activity',
                )
            target_position = target_positions[0]
            if target_position == position:
                raise InvalidPipelineStepsError(
                    field_name=(
                        f'steps.{position}.dependsOn.{dependency_position}.activity'
                    ),
                    message='must not reference its own Activity',
                )
            dependencies.append(target_position)
        dependencies_by_position[position] = tuple(dependencies)

    visiting: set[int] = set()
    visited: set[int] = set()

    def visit(position: int) -> None:
        """Reject one traversal edge that returns to an active path."""

        if position in visiting:
            raise InvalidPipelineStepsError(
                field_name='steps',
                message='must not contain dependency cycles',
            )
        if position in visited:
            return
        visiting.add(position)
        for target_position in dependencies_by_position[position]:
            visit(target_position)
        visiting.remove(position)
        visited.add(position)

    for position in dependencies_by_position:
        visit(position)


def step_content(step: PipelineStep) -> JsonObject:
    """Serialize one domain step without adding execution data."""

    return {
        'activity_id': step.activity_id,
        'depends_on': [
            {
                'activity_id': dependency.activity_id,
                'condition': dependency.condition,
            }
            for dependency in step.depends_on
        ],
    }


def document_content(document: PipelineDocument) -> JsonObject:
    """Serialize a complete pipeline for changelog snapshots."""

    return {
        "id": document.id,
        "name": document.name,
        "description": document.description,
        "enabled": document.enabled,
        "status": document.status,
        "harness": {
            'kind': document.harness.kind,
            'version': document.harness.version,
            'config': dict(document.harness.config),
        },
        "steps": [step_content(step) for step in document.steps],
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
    }
