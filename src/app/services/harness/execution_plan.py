"""Execution plan helpers for harness service."""

from src.app.schemas import (
    ExecutionPlan,
    GeneratorAssignment,
    ReviewerAssignment,
    RunHarnessRequest,
)


def build_static_execution_plan(req: RunHarnessRequest) -> ExecutionPlan:
    """
    Build a deterministic fallback for direct harness calls.

    Planned task runs should supply execution_plan. This fallback preserves the
    low-level API for callers that want to configure the harness explicitly.
    """
    if not req.reviewer_skills:
        raise ValueError(
            'At least one reviewer skill is required without an execution plan'
        )

    return ExecutionPlan(
        phase='mvp',
        reasoning='Static execution configuration supplied by the caller.',
        generator=GeneratorAssignment(
            persona=req.generator_persona,
            skills=req.generator_skills,
            focus='Implement the requested change with minimal safe modifications.',
        ),
        reviewers=[
            ReviewerAssignment(
                persona=req.reviewer_persona,
                skills=[skill_id],
                strictness=55,
                focus='Review the requested change using the assigned skill.',
            )
            for skill_id in req.reviewer_skills
        ],
    )
