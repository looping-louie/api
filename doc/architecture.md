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
|   `-- library.py                 Builds immutable SQL snapshots
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
|   |-- service.py                 Coordinates resource operations
|   |-- types.py                   Defines contracts and domain errors
|   `-- validation.py              Normalizes and validates input
|-- loop_runs/
|   |-- __init__.py                Defines the package's public imports
|   |-- generation.py              Orchestrates model calls for direct and
|   |                              roundtable runs
|   |-- service.py                 Creates, reads, and advances records through
|   |                              checkpoints
|   |-- types.py                   Defines contracts and domain errors
|   `-- validation.py              Normalizes and validates input
|-- loops/
|   |-- __init__.py                Defines the package's public imports
|   |-- catalog_seeder.py          Installs curated catalog entries in workspaces
|   |-- mutation.py                Builds updates and changelog data
|   |-- service.py                 Coordinates definitions and changelogs
|   |-- types.py                   Defines input types and domain errors
|   `-- validation.py              Normalizes and validates definitions
|-- model_execution/
|   |-- __init__.py                Defines the package's public imports
|   `-- service.py                 Resolves enabled workspace deployments and
|                                  invokes provider-neutral endpoints
|-- models/
|   |-- __init__.py                Defines the package's public imports
|   |-- availability.py            Calculates workspace availability
|   `-- service.py                 Queries the curated catalog
|-- personas/
|   |-- __init__.py                Defines the package's public imports
|   |-- service.py                 Manages workspace resources and skill links
|   `-- types.py                   Defines contracts and associations
|-- pipelines/
|   |-- __init__.py                Defines the package's public imports
|   |-- mutation.py                Builds updates and changelog diffs
|   |-- operations.py              Provides shared use-case operations
|   |-- service.py                 Coordinates definitions and history
|   |-- types.py                   Defines input types and domain errors
|   `-- validation.py              Normalizes and validates definitions
|-- providers/
|   |-- __init__.py                Defines the package's public imports
|   |-- configuration.py           Interprets and validates settings
|   |-- connection.py              Tests configured connectivity
|   |-- errors.py                  Defines configuration errors
|   |-- model_registry.py          Queries catalog models by provider
|   |-- secret.py                  Encrypts, decrypts, and masks API keys
|   `-- service.py                 Coordinates configuration and checks
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
|   |-- metadata_validator.py      Validates structured metadata
|   `-- service.py                 Manages workspace resources
`-- task_checkpoint/
  |-- __init__.py                Defines the package's public imports
  `-- service.py                 Parses and validates filesystem operations
```

### Catalogs

This package defines immutable, application-shipped data. It contains curated
Python definitions and typed loaders for manifest-backed Markdown resources.
It does not access SQLite or workspace state.

```text
catalogs/
|
|-- __init__.py                    Exposes the combined instruction catalog
|-- instructions/
|   |-- __init__.py                Defines public catalog contracts
|   |-- entries.py                 Defines immutable persona and skill entries
|   |-- errors.py                  Defines catalog loading errors
|   |-- loader.py                  Loads catalogs and validates cross-references
|   |-- resource_loader.py         Loads JSON manifests and Markdown resources
|   |-- resource_validation.py     Validates manifest values
|   `-- types.py                   Defines catalog metadata and value types
|-- loops/
|   |-- __init__.py                Defines public catalog contracts
|   `-- catalog.py                 Defines curated entries
|-- models/
|   |-- __init__.py                Combines and validates curated entries
|   |-- helpers.py                 Builds shared pricing and capability values
|   |-- nvidia.py                  Defines NVIDIA entries
|   |-- primary.py                 Defines primary provider entries
|   |-- secondary.py               Defines secondary provider entries
|   |-- types.py                   Defines catalog contracts
|   `-- validation.py              Validates catalog consistency
|-- personas/
|   |-- __init__.py                Declares packaged resources
|   |-- content/                   Contains Markdown definitions
|   |-- loader.py                  Loads and validates entries
|   `-- registry.json              Declares resource metadata
|-- providers/
|   |-- __init__.py                Defines public catalog contracts
|   `-- catalog.py                 Defines supported provider metadata
`-- skills/
  |-- __init__.py                Declares packaged resources
  |-- content/                   Contains Markdown definitions
  |-- loader.py                  Loads and validates entries
  `-- registry.json              Declares resource metadata
```

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
