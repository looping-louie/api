"""Normalization and aggregate validation rules for loops."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import cast

from src.app.models.loop import (
    JsonObject,
    LoopAgent,
    LoopAgentRole,
    LoopDocument,
    LoopOutputContract,
    LoopOutputType,
    LoopStopConditions,
)


def require_text(value: object, field_name: str) -> str:
    """Return stripped non-empty text or raise loop validation."""

    from src.app.services.loops.types import LoopValidationError

    if not isinstance(value, str) or not value.strip():
        raise LoopValidationError(
            field_name=field_name,
            message="must be a non-empty string",
        )
    return value.strip()


def normalize_description(value: object) -> str:
    """Return stripped description text."""

    from src.app.services.loops.types import LoopValidationError

    if not isinstance(value, str):
        raise LoopValidationError(
            field_name="description",
            message="must be a string",
        )
    return value.strip()


def normalize_stop_conditions(value: object) -> LoopStopConditions:
    """Validate positive supplied stop conditions and require one."""

    from src.app.services.loops.types import LoopValidationError

    if not isinstance(value, LoopStopConditions):
        raise LoopValidationError(
            field_name="stop_conditions",
            message="must be a stop conditions object",
        )
    supplied = {
        "max_iterations": value.max_iterations,
        "max_tokens": value.max_tokens,
        "timeout_seconds": value.timeout_seconds,
    }
    if all(item is None for item in supplied.values()):
        raise LoopValidationError(
            field_name="stop_conditions",
            message="must configure at least one condition",
        )
    for field_name, item in supplied.items():
        if item is None:
            continue
        if isinstance(item, bool) or not isinstance(item, int) or item < 1:
            raise LoopValidationError(
                field_name=f"stop_conditions.{field_name}",
                message="must be a positive integer",
            )
    return value


def normalize_agents(
    value: object,
    id_factory: Callable[[], str],
) -> tuple[LoopAgent, ...]:
    """Normalize agent inputs and generate omitted identifiers."""

    from src.app.services.loops.types import (
        LoopAgentInput,
        LoopValidationError,
    )

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise LoopValidationError(
            field_name="agents",
            message="must be an array",
        )
    agents: list[LoopAgent] = []
    for position, item in enumerate(value):
        if not isinstance(item, LoopAgentInput):
            raise LoopValidationError(
                field_name=f"agents.{position}",
                message="must be an agent object",
            )
        role = require_text(item.role, f"agents.{position}.role")
        if role not in {"generator", "reviewer", "aggregator"}:
            raise LoopValidationError(
                field_name=f"agents.{position}.role",
                message="must be generator, reviewer, or aggregator",
            )
        agents.append(
            LoopAgent(
                id=(
                    require_text(item.id, f"agents.{position}.id")
                    if item.id is not None
                    else id_factory()
                ),
                model_id=require_text(
                    item.model_id, f"agents.{position}.model_id"
                ),
                persona_id=require_text(
                    item.persona_id, f"agents.{position}.persona_id"
                ),
                role=cast(LoopAgentRole, role),
            )
        )
    identifiers = [agent.id for agent in agents]
    if len(set(identifiers)) != len(identifiers):
        raise LoopValidationError(
            field_name="agents.id",
            message="must be unique within a loop",
        )
    return tuple(agents)


def normalize_output_contract(value: object) -> LoopOutputContract:
    """Validate the generic output contract."""

    from src.app.services.loops.types import LoopValidationError

    if not isinstance(value, LoopOutputContract):
        raise LoopValidationError(
            field_name="output_contract",
            message="must be an output contract object",
        )
    output_type = require_text(value.type, "output_contract.type")
    if output_type not in {"text", "json", "files"}:
        raise LoopValidationError(
            field_name="output_contract.type",
            message="must be text, json, or files",
        )
    description = require_text(
        value.description, "output_contract.description"
    )
    files = tuple(
        require_text(path, f"output_contract.files.{position}")
        for position, path in enumerate(value.files)
    )
    if output_type == "files" and not files:
        raise LoopValidationError(
            field_name="output_contract.files",
            message="must contain at least one path for files output",
        )
    if output_type == "json" and value.schema is None:
        raise LoopValidationError(
            field_name="output_contract.schema",
            message="is required for json output",
        )
    if value.schema is not None and not isinstance(value.schema, dict):
        raise LoopValidationError(
            field_name="output_contract.schema",
            message="must be a JSON object",
        )
    return LoopOutputContract(
        type=cast(LoopOutputType, output_type),
        description=description,
        files=files,
        schema=value.schema,
    )


def validate_loop(document: LoopDocument) -> None:
    """Validate role cardinality for the loop's selected flow."""

    from src.app.services.loops.types import LoopValidationError

    counts = {
        role: sum(agent.role == role for agent in document.agents)
        for role in ("generator", "reviewer", "aggregator")
    }
    invalid = False
    if document.flow == "direct":
        invalid = not document.agents or counts["aggregator"] > 1
    elif document.flow == "refinement":
        invalid = (
            counts["generator"] != 1
            or counts["reviewer"] < 1
            or counts["aggregator"] > 1
        )
    elif document.flow == "roundtable":
        invalid = (
            counts["generator"] < 2
            or counts["aggregator"] != 1
        )
    if invalid:
        raise LoopValidationError(
            field_name="agents",
            message=f"role combination is invalid for {document.flow} flow",
        )


def document_content(document: LoopDocument) -> JsonObject:
    """Return the complete public loop representation for audit storage."""

    return {
        "id": document.id,
        "title": document.title,
        "description": document.description,
        "flow": document.flow,
        "status": document.status,
        "stop_conditions": {
            "max_iterations": document.stop_conditions.max_iterations,
            "max_tokens": document.stop_conditions.max_tokens,
            "timeout_seconds": document.stop_conditions.timeout_seconds,
        },
        "agents": [
            {
                "id": agent.id,
                "model_id": agent.model_id,
                "persona_id": agent.persona_id,
                "role": agent.role,
            }
            for agent in document.agents
        ],
        "output_contract": {
            "type": document.output_contract.type,
            "description": document.output_contract.description,
            "files": list(document.output_contract.files),
            "schema": document.output_contract.schema,
        },
        "created_at": document.created_at.isoformat(),
        "created_by": document.created_by,
        "updated_at": document.updated_at.isoformat(),
        "updated_by": document.updated_by,
    }
