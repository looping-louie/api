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

This package implements application use cases and reusable business rules. It
coordinates catalog definitions, domain models, and repositories without
handling FastAPI request-response concerns or direct persistence.

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

### Controllers

This package translates HTTP schemas to application service calls and
application results to HTTP schemas. Resource packages compose endpoint-specific
controllers for router compatibility; routers retain route declarations,
dependency injection, and request extraction.

```text
controllers/
|
|-- activity.py                   Translates activity HTTP operations
|-- loop/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- create.py                 Creates definitions
|   |-- delete.py                 Deletes definitions
|   |-- describe.py               Describes one definition
|   |-- list.py                   Lists definitions
|   |-- list_changelog.py         Lists changelog entries
|   |-- patch.py                  Applies supplied changes
|   `-- utils.py                  Translates request schemas to service inputs
|-- loop_run.py                   Translates run and checkpoint operations
|-- model/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- describe.py               Describes one curated entry
|   `-- list.py                   Lists curated entries and availability
|-- persona/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- create.py                 Creates resources
|   |-- delete.py                 Deletes resources
|   |-- describe.py               Describes one resource
|   |-- list.py                   Lists resources
|   `-- patch.py                  Applies supplied changes
|-- pipeline/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- create.py                 Creates definitions
|   |-- delete.py                 Deletes definitions
|   |-- describe.py               Describes one definition
|   |-- list.py                   Lists definitions
|   |-- list_changelog.py         Lists changelog entries
|   |-- patch.py                  Applies supplied changes
|   `-- utils.py                  Translates request schemas to service inputs
|-- provider/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- delete.py                 Deletes configuration
|   |-- describe.py               Describes one configuration
|   |-- list.py                   Lists configurations
|   `-- patch.py                  Applies supplied changes
`-- skill/
    |-- __init__.py               Composes endpoint-specific controllers
    |-- create.py                 Creates resources
    |-- delete.py                 Deletes resources
    |-- describe.py               Describes one resource
    |-- list.py                   Lists resources
    `-- patch.py                  Applies supplied changes
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

This package implements application persistence with SQLite. Resource packages
define repository contracts, mappings, and adapters; shared adapters support
cross-resource lookups; infrastructure owns database setup and migrations.

```text
repositories/
|
|-- __init__.py                    Declares persistence implementations
|-- infrastructure/
|   |-- __init__.py                Declares database setup utilities
|   |-- local_tenant_seed.py       Creates the initial local workspace
|   |-- migration_runner.py         Discovers and applies SQLite migrations
|   `-- sqlite_database.py          Manages asynchronous SQLite connections
|-- instructions/
|   |-- __init__.py                Declares persona and skill persistence
|   |-- availability.py            Persists workspace availability settings
|   |-- mapping.py                 Maps SQLite rows and normalizes values
|   |-- mutations.py               Creates, updates, and deletes records
|   |-- repository.py              Persists resource definitions
|   |-- settings.py                Persists workspace enablement settings
|   `-- persona_skill_repository.py Persists persona-skill associations
|-- loop_runs/
|   |-- __init__.py                Defines public persistence imports
|   |-- errors.py                  Defines checkpoint transition conflicts
|   |-- repository.py              Defines the persistence contract
|   `-- sqlite_repository.py       Persists checkpoint records
|-- loops/
|   |-- __init__.py                Declares persistence contracts and helpers
|   |-- mapping.py                 Maps SQLite rows and write values
|   |-- repository.py              Defines the persistence contract and changelog
|   `-- sqlite_repository.py       Persists records and changelog entries
|-- pipelines/
|   |-- __init__.py                Declares persistence contracts and adapters
|   |-- mapping.py                 Maps SQLite rows and write values
|   |-- repository.py              Defines the persistence contract
|   `-- sqlite_repository.py       Persists records and changelog entries
|-- providers/
|   |-- __init__.py                Declares credential persistence and adapters
|   |-- credential_mapper.py       Maps SQLite credential rows
|   |-- repository.py              Persists encrypted credentials
|   `-- state_repository.py        Exposes connection state to availability
`-- shared/
  |-- __init__.py                Declares reusable persistence adapters
  |-- dependency_repository.py   Looks up resource dependencies
  |-- json_mapping.py            Serializes and deserializes JSON values
  |-- reference_repository.py    Resolves instruction and model references
  |-- tenant_repository.py       Persists workspace memberships
  `-- validation_repository.py   Looks up normalized resource names
```

### Models

This package defines typed internal domain state. It contains persisted
documents, immutable changelog entries, availability projections, and values
used between services and repositories. It does not define HTTP contracts.

```text
models/
|
|-- changelog.py                   Defines shared immutable changelog values
|-- instruction.py                 Defines persisted and available resource data
|-- loop.py                        Defines definitions, agents, output, and history
|-- loop_run.py                    Defines execution state and checkpoints
|-- model.py                       Defines catalog and availability projections
|-- persona.py                     Defines resource documents with skill links
|-- pipeline.py                    Defines definitions, steps, and history
|-- provider.py                    Defines credential and safe configuration state
|-- reference.py                   Defines dependency and reference values
`-- tenant.py                      Defines workspace and membership state
```

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
