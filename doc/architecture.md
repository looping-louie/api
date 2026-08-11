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

## Repository structure

Application code lives under `src/app` and is organized by responsibility:

```text
src/app/
|
|-- bootstrap/       Application startup and dependency wiring
|-- catalogs/        Builtin providers, models, loops, personas, and skills
|-- controllers/     HTTP-level use-case orchestration
|-- middleware/      Cross-cutting HTTP middleware
|-- models/          Internal domain entities
|-- repositories/    Persistence and data access
|-- routers/         FastAPI route composition
|-- schemas/         HTTP contracts and shared schemas
|-- services/        Application and domain services
`-- utils/           Shared HTTP and utility code
```

### Services

This package <ADD DESCRIPTION HERE>.

```text
services/
|
|-- __init__.py                    Declares the services package
|-- execution_instructions/
|   |-- __init__.py                Defines the package's public imports
|   `-- library.py                 Builds immutable SQL instruction snapshots
|                                  for prompt assembly
|-- instructions/
|   |-- __init__.py                Defines the package's public imports
|   |-- catalog/
|   |   |-- __init__.py            Defines the package's public imports
|   |   |-- serialization.py       Serializes catalog entries for persistence
|   |   `-- synchronizer.py        Materializes builtins in SQLite, applies
|   |                              version and checksum policy, deprecates
|   |                              removed entries, and synchronizes
|   |                              persona-skill associations
|   |-- service.py                 Coordinates instruction resource operations
|   |-- types.py                   Defines instruction contracts and domain errors
|   `-- validation.py              Normalizes and validates instruction input
|-- loop_runs/
|   |-- __init__.py                Defines the package's public imports
|   |-- generation.py              Orchestrates model calls for direct and
|   |                              roundtable loop runs
|   |-- service.py                 Creates, reads, and advances loop-run
|   |                              records through checkpoints
|   |-- types.py                   Defines loop-run contracts and domain errors
|   `-- validation.py              Normalizes and validates loop-run input
|-- loops/
|   |-- __init__.py                Defines the package's public imports
|   |-- catalog_seeder.py          Installs curated catalog loops in workspaces
|   |-- mutation.py                Builds loop updates and changelog data
|   |-- service.py                 Coordinates loop definitions and changelogs
|   |-- types.py                   Defines loop input types and domain errors
|   `-- validation.py              Normalizes and validates loop definitions
|-- model_execution/
|   |-- __init__.py                Defines the package's public imports
|   `-- service.py                 Resolves enabled workspace deployments and
|                                  invokes provider-neutral model endpoints
|-- models/
|   |-- __init__.py                Defines the package's public imports
|   |-- availability.py            Calculates workspace model availability
|   `-- service.py                 Queries the curated model catalog
|-- personas/
|   |-- __init__.py                Defines the package's public imports
|   |-- service.py                 Manages workspace personas and skill links
|   `-- types.py                   Defines persona contracts and associations
|-- pipelines/
|   |-- __init__.py                Defines the package's public imports
|   |-- mutation.py                Builds pipeline updates and changelog diffs
|   |-- operations.py              Provides shared pipeline use-case operations
|   |-- service.py                 Coordinates pipeline definitions and history
|   |-- types.py                   Defines pipeline input types and domain errors
|   `-- validation.py              Normalizes and validates pipeline definitions
|-- providers/
|   |-- __init__.py                Defines the package's public imports
|   |-- configuration.py           Interprets and validates provider settings
|   |-- connection.py              Tests configured provider connectivity
|   |-- errors.py                  Defines provider configuration errors
|   |-- model_registry.py          Queries catalog models by provider
|   |-- secret.py                  Encrypts, decrypts, and masks API keys
|   `-- service.py                 Coordinates provider configuration and checks
|-- shared/
|   |-- __init__.py                Declares shared service utilities
|   |-- changelog.py               Builds changelog metadata and field diffs
|   |-- dependency_checker.py      Prevents deletion of referenced resources
|   |-- generation.py              Creates resource IDs and UTC timestamps
|   |-- pagination.py              Defines fixed-size offset pagination rules
|   |-- reference_resolver.py      Resolves references between workspace resources
|   |-- settings.py                Loads environment-backed application settings
|   |-- tenant.py                  Resolves workspace tenancy and memberships
|   `-- validation.py              Provides reusable domain validations
|-- skills/
|   |-- __init__.py                Defines the package's public imports
|   |-- metadata_validator.py      Validates structured skill metadata
|   `-- service.py                 Manages workspace skill resources
`-- task_checkpoint/
  |-- __init__.py                Defines the package's public imports
  `-- service.py                 Parses and validates file operations
```

### Catalogs

This package <ADD DESCRIPTION HERE>.

Internally, contains the following packages and modules:

- `personas` contain the packaged builtin persona registries,
  Markdown resources, and typed loaders.
- `skills` contain the packaged builtin skill registries,
  Markdown resources, and typed loaders.
- `instructions` provides the shared catalog entry types,
  resource validation, and combined loader. It loads and validates immutable
  packaged resources without knowing about SQLite or application bootstrap.

### Repositories

This package <ADD DESCRIPTION HERE>.

### Models

This package <ADD DESCRIPTION HERE>.

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
