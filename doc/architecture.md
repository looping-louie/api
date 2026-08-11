# Looping Louie Architecture

Looping Louie API is the decision engine for iterative LLM software
development. It orchestrates generators, reviewers, and aggregators while the
CLI executes repository changes locally.

The runtime is independent from any programming language, framework, or LLM
provider.

## Ownership boundaries

The API owns resource management, loop-run state, prompt generation, model
decisions, and checkpoint transitions. The CLI owns workspace lifecycle,
repository inspection, filesystem changes, Git operations, and multi-step
workflow progression.

The API and CLI coordinate through the loop-run checkpoint protocol documented
in [Execution](components/execution.md). The API never mutates the target
repository directly, and the CLI does not make model or reviewer decisions.

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
    catalogs/        Builtin providers, models, loops, personas, and skills
    controllers/     HTTP-level use-case orchestration
    middleware/      Cross-cutting HTTP middleware
    models/          Internal domain entities
    repositories/    Persistence and data access
    routers/         FastAPI route composition
    schemas/         HTTP contracts and shared schemas
    services/        Application and domain services
    utils/           Shared HTTP and utility code
```

A more in-depth description of the module and packages:

- `src/app/catalogs/personas` contain the packaged builtin persona registries,
  Markdown resources, and typed loaders.
- `src/app/catalogs/skills` contain the packaged builtin skill registries,
  Markdown resources, and typed loaders.
- `src/app/catalogs/instructions` provides the shared catalog entry types,
  resource validation, and combined loader. It loads and validates immutable
  packaged resources without knowing about SQLite or application bootstrap.
- `src/app/services/instructions/service.py` owns `InstructionService`, its
  repository protocol, shared documents, DTOs, types, and domain errors.
- `src/app/services/instructions/catalog_synchronizer.py` materializes builtin
  catalog entries in SQLite, applies catalog version and checksum policy,
  deprecates removed entries, and synchronizes persona-skill associations.
- `src/app/services/instructions/catalog_serialization.py` is the
  package-private persistence serializer used by the catalog synchronizer.
- `src/app/services/execution_instructions/library.py` builds immutable,
  workspace-specific SQL instruction snapshots for prompt assembly.
- `src/app/services/model_execution/service.py` resolves enabled workspace
  deployments and invokes their provider-neutral model endpoints.
- `src/app/services/execution_instructions/__init__.py` define their packages'
  public imports.
- `src/app/services/instructions/__init__.py` define their packages' public
  imports.
