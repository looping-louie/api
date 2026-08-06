# Looping Louie Architecture

Looping Louie API is the decision engine for iterative LLM software
development. It orchestrates generators, reviewers, and aggregators while the
CLI executes repository changes locally.

The runtime is independent from any programming language, framework, or LLM
provider.

## Components

- [Execution](components/execution.md) describes persisted runs, checkpoints,
  prompts, review, finalisation, artefacts, and metrics.
- [Loops and roles](components/loops-and-roles.md) defines loop flows, agent
  roles, and the loop-run behavior implemented today.
- [Instruction catalog](components/instruction-catalog.md) describes builtin
  instruction ownership, synchronization, and maintenance.
- [Providers](components/providers.md) records provider and model-catalog
  boundaries.
- [Philosophy](components/philosophy.md) contains the project principles and
  long-term direction.
- [Current limitations](components/limitations.md) records known MVP
  boundaries.

## Repository structure

Application code lives under `src/app` and is organized by responsibility:

```text
src/app/
    bootstrap/       Application startup and dependency wiring
    catalogs/        Builtin providers, models, loops, and instructions
    controllers/     HTTP-level use-case orchestration
    middleware/      Cross-cutting HTTP middleware
    models/          Internal domain entities
    repositories/    Persistence and data access
    routers/         FastAPI route composition
    schemas/         HTTP contracts and shared schemas
    services/        Application and domain services
    skills/          Packaged instruction loading and validation
    utils/           Shared HTTP and utility code
```

## Ownership boundaries

The API owns resource management, loop-run state, prompt generation, model
decisions, and checkpoint transitions. The CLI owns workspace lifecycle,
repository inspection, filesystem changes, Git operations, and multi-step
workflow progression.

The API and CLI coordinate through the loop-run checkpoint protocol documented
in [Execution](components/execution.md). The API never mutates the target
repository directly, and the CLI does not make model or reviewer decisions.
