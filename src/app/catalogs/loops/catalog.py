"""Curated loop definitions installed into each workspace."""

from __future__ import annotations

from dataclasses import dataclass

from src.app.models.loop import (
    JsonObject,
    LoopAgentRole,
    LoopFlow,
    LoopOutputType,
)


SHAPE_IDEAS_CONTRACT = """
Produce one Markdown document of at most 1000 words.

Use exactly this structure and heading order:

# Idea title

## Thesis
One sentence explaining what should be achieved.

## Customer and problem
Who has the problem, what they are trying to do, and how they solve it today.

## Desired outcome
The observable change the idea should create.

## Proposed solution
The solution concept and primary experience without exhaustive design.

## Appetite
How much effort should be invested and which constraint shapes that decision.

## Scope
What the first version must include.

## Non-goals
What is explicitly excluded.

## Risks and rabbit holes
Assumptions, dependencies, and scope-expansion risks.

## Validation
What must be tested before or during implementation.

## Success criteria
How the team will know the idea works.

## Open decisions
Decisions that still require an answer.

Return the Markdown document only.
""".strip()

PLAN_IMPLEMENTATION_CONTRACT = """
Produce valid JSON containing an array of implementation tasks.

Every task must have exactly this shape:

{
  "id": "ideas-001",
  "status": "pending",
  "prompt": "Self-contained implementation instruction with acceptance criteria.",
  "run_id": "",
  "commit_message": "Specific imperative commit message"
}

Rules:
- Return the JSON array only.
- Task ids must be unique and end in a three-digit sequence.
- status must always be "pending".
- run_id must always be an empty string.
- Each task must be independently implementable and reviewable.
- Tasks must be ordered by dependency.
- Each prompt must preserve the approved scope and non-goals.
- Each prompt must include enough context and acceptance criteria to execute
  without reading the prior discussion.
- Each task should produce one small, coherent commit.
""".strip()

TASKS_SCHEMA: JsonObject = {
    "type": "array",
    "minItems": 1,
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "id",
            "status",
            "prompt",
            "run_id",
            "commit_message",
        ],
        "properties": {
            "id": {
                "type": "string",
                "pattern": "^[a-z][a-z0-9-]*-[0-9]{3}$",
            },
            "status": {"const": "pending"},
            "prompt": {"type": "string", "minLength": 1},
            "run_id": {"const": ""},
            "commit_message": {"type": "string", "minLength": 1},
        },
    },
}


@dataclass(frozen=True, slots=True)
class LoopCatalogAgent:
    """One predefined agent assignment without a persisted identifier."""

    model_id: str
    persona_id: str
    role: LoopAgentRole


@dataclass(frozen=True, slots=True)
class LoopCatalogEntry:
    """One predefined loop installed as an ordinary workspace resource."""

    id: str
    title: str
    description: str
    flow: LoopFlow
    max_iterations: int
    agents: tuple[LoopCatalogAgent, ...]
    output_type: LoopOutputType
    output_description: str
    output_files: tuple[str, ...]
    output_schema: JsonObject | None = None


def _agent(persona_key: str, role: LoopAgentRole) -> LoopCatalogAgent:
    """Build one catalog agent with the selected shared model."""

    return LoopCatalogAgent(
        model_id="deepseek-v4-pro",
        persona_id=f"builtin:persona:{persona_key}",
        role=role,
    )


LOOP_CATALOG: tuple[LoopCatalogEntry, ...] = (
    LoopCatalogEntry(
        id="builtin:loop:shape-ideas",
        title="shape ideas",
        description=(
            "Shape an initial idea into a focused, validated product brief."
        ),
        flow="roundtable",
        max_iterations=3,
        agents=(
            _agent("product_manager", "generator"),
            _agent("ux_designer", "generator"),
            _agent("devils_advocate", "reviewer"),
            _agent("editor", "aggregator"),
        ),
        output_type="files",
        output_description=SHAPE_IDEAS_CONTRACT,
        output_files=("ideas.md",),
    ),
    LoopCatalogEntry(
        id="builtin:loop:plan-implementation",
        title="plan implementation",
        description=(
            "Turn an approved idea into ordered, independently executable tasks."
        ),
        flow="roundtable",
        max_iterations=3,
        agents=(
            _agent("tech_lead", "generator"),
            _agent("platform_architect", "generator"),
            _agent("devils_advocate", "reviewer"),
            _agent("editor", "aggregator"),
        ),
        output_type="files",
        output_description=PLAN_IMPLEMENTATION_CONTRACT,
        output_files=("tasks.json",),
        output_schema=TASKS_SCHEMA,
    ),
)


__all__ = [
    "LOOP_CATALOG",
    "LoopCatalogAgent",
    "LoopCatalogEntry",
    "PLAN_IMPLEMENTATION_CONTRACT",
    "SHAPE_IDEAS_CONTRACT",
    "TASKS_SCHEMA",
]
