# Looping Louie API Software Architecture

This document describes the software architecture of the Looping Louie API.
The cross-repository product architecture is documented on the
[Looping Louie documentation site](https://loopinglouie.ai/docs/architecture/).
The API and runtime checkpoint contract is documented in
[Execution lifecycle](components/execution-lifecycle.md).

## Repository structure

Application code lives under `src/app` and is organized by responsibility:

```text
src/app/
|
|-- bootstrap/       Application startup and dependency wiring
|-- catalogs/        Builtin providers, models, personas, and skills
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

Service package names identify a bounded context and use plural nouns. A
package's primary use-case coordinator uses `service.py`; narrower modules use
the responsibility they own. `catalog.py` provides a domain's curated catalog
view, `static.py` exposes application-shipped definitions without workspace
state, and `synchronization/` materializes packaged definitions into SQLite.

```text
services/
|
|-- __init__.py                    Declares the services package
|-- activities/
|   |-- __init__.py                Defines the package's public imports
|   `-- service.py                 Manages definitions and changelog history
|-- activity_runs/
|   |-- __init__.py                Defines the package's public imports
|   |-- generation.py              Orchestrates model calls for loop Activities
|   |-- harness_result.py          Dispatches normalized Harness observations
|   |                              and merges their Git outcome
|   |-- operation_plan.py          Validates model-generated filesystem changes
|   |-- service.py                 Creates, reads, and advances activity-owned
|   |                              execution checkpoints
|   `-- types.py                   Defines execution contracts and domain errors
|-- catalogs/
|   |-- __init__.py                Defines the package's public imports
|   `-- static.py                  Exposes static provider and model definitions
|-- execution_instructions/
|   |-- __init__.py                Defines the package's public imports
|   `-- library.py                 Builds immutable SQL snapshots
|                                  for prompt assembly
|-- persona_skills/
|   |-- __init__.py                Defines the package's public imports
|   |-- definitions.py             Binds lifecycle behavior to Persona and Skill
|   |-- lifecycle.py               Shares private definition persistence mechanics
|   |-- synchronization/
|   |   |-- __init__.py            Defines the package's public imports
|   |   |-- serialization.py       Serializes catalog entries for persistence
|   |   `-- synchronizer.py        Materializes builtins in SQLite, applies
|   |                              version and checksum policy, deprecates
|   |                              removed entries, and synchronizes
|   |                              persona-skill associations
|   |-- types.py                   Defines contracts and domain errors
|   `-- validation.py              Normalizes and validates input
|-- linked_services/
|   |-- __init__.py                Defines the package's public imports
|   `-- service.py                 Manages User-owned provider connections
|-- models/
|   |-- __init__.py                Defines the package's public imports
|   |-- availability.py            Calculates current-User availability
|   |-- catalog.py                 Queries the curated model catalog
|   `-- model_execution.py         Invokes provider-neutral endpoints through
|                                  an explicit Linked Service
|-- personas/
|   |-- __init__.py                Defines the package's public imports
|   |-- service.py                 Manages user-owned resources and skill links
|   `-- types.py                   Defines contracts and associations
|-- pipelines/
|   |-- __init__.py                Defines the package's public imports
|   |-- mutation.py                Builds updates and changelog diffs
|   |-- operations.py              Provides shared use-case operations
|   |-- service.py                 Coordinates definitions and history
|   |-- types.py                   Defines input types and domain errors
|   `-- validation.py              Normalizes and validates definitions
|-- pipeline_runs/
|   |-- __init__.py                Defines the package's public imports
|   |-- etag.py                    Creates concurrency entity tags
|   |-- events.py                  Builds scheduler and Harness ledger events
|   |-- graph.py                   Reads frozen dependency requirements
|   |-- readiness.py               Diagnoses queued-run Worker availability
|   |-- service.py                 Creates, reads, and advances Pipeline runs
|   |-- snapshot.py                Freezes models, Harnesses, and instructions
|   `-- types.py                   Defines execution errors
|-- providers/
|   |-- __init__.py                Defines the package's public imports
|   |-- configuration.py           Provides pure configuration helpers
|   |-- connection.py              Tests configured connectivity
|   |-- errors.py                  Defines configuration errors
|   `-- secret.py                  Encrypts, decrypts, and masks API keys
|-- shared/
|   |-- __init__.py                Declares shared service utilities
|   |-- changelog.py               Builds changelog metadata and field diffs
|   |-- dependency_checker.py      Prevents deletion of referenced resources
|   |-- generation.py              Creates resource IDs and UTC timestamps
|   |-- pagination.py              Defines fixed-size offset pagination rules
|   |-- reference_resolver.py      Resolves references between Project resources
|   |-- settings.py                Loads environment-backed application settings
|   |-- tenant.py                  Resolves Project tenancy and memberships
|   `-- validation.py              Provides reusable domain validations
|-- skills/
|   |-- __init__.py                Defines the package's public imports
|   |-- metadata_validator.py      Validates structured metadata
|   |-- service.py                 Manages Project resources
|   `-- types.py                   Defines Skill lifecycle input contracts
|-- users/
|   |-- __init__.py                Defines the package's public imports
|   `-- service.py                 Manages durable request identities
|-- worker_instances/
|   |-- __init__.py                Defines the package's public imports
|   `-- service.py                 Manages User-owned Workers, Project enablements, and capacity
|-- projects/
|   |-- __init__.py                Defines the package's public imports
|   `-- service.py                 Manages User-owned execution-placement Projects
```

### Controllers

This package translates HTTP schemas to application service calls and
application results to HTTP schemas. Resource packages compose endpoint-specific
controllers for router compatibility; routers retain route declarations,
dependency injection, and request extraction.

```text
controllers/
|
|-- catalogs/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- list_models.py            Lists static model definitions
|   |-- list_personas.py          Lists built-in Persona definitions
|   |-- list_providers.py         Lists static provider definitions
|   |-- list_skills.py            Lists built-in Skill definitions
|   `-- utils.py                  Validates catalog definition versions
|-- activities/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- create.py                 Creates definitions
|   |-- delete.py                 Deletes definitions
|   |-- describe.py               Describes one definition
|   |-- list.py                   Lists definitions
|   |-- list_changelog.py         Lists changelog entries
|   |-- patch.py                  Applies supplied changes
|   `-- utils.py                  Translates patch schemas to service changes
|-- activity_runs/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- continue_run.py           Advances execution checkpoints
|   |-- describe.py               Retrieves one execution checkpoint
|   |-- list.py                   Lists execution checkpoints
|   `-- utils.py                  Translates checkpoint results to responses
|-- linked_services/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- create.py                 Creates Linked Services
|   |-- delete.py                 Deletes Linked Services
|   |-- describe.py               Retrieves one Linked Service
|   |-- list.py                   Lists Linked Services
|   |-- patch.py                  Updates Linked Services
|   `-- response.py               Translates Linked Service responses
|-- personas/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- create.py                 Creates resources
|   |-- delete.py                 Deletes resources
|   |-- describe.py               Describes one resource
|   |-- list.py                   Lists resources
|   |-- patch.py                  Applies supplied changes
|   `-- response.py               Translates Persona documents to responses
|-- pipelines/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- create.py                 Creates definitions
|   |-- delete.py                 Deletes definitions
|   |-- describe.py               Describes one definition
|   |-- list.py                   Lists definitions
|   |-- list_changelog.py         Lists changelog entries
|   |-- patch.py                  Applies supplied changes
|   |-- run.py                    Coordinates Pipeline-run operations
|   `-- utils.py                  Translates request schemas to service inputs
|-- skills/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- create.py                 Creates resources
|   |-- delete.py                 Deletes resources
|   |-- describe.py               Describes one resource
|   |-- list.py                   Lists resources
|   `-- patch.py                  Applies supplied changes
|-- projects/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- create.py                 Creates Projects
|   |-- describe.py               Describes one Project
|   |-- list.py                   Lists accessible Projects
|   |-- patch.py                  Applies Project metadata changes
|   `-- response.py               Translates Project documents to responses
|-- worker_instances/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- create.py                 Registers Workers
|   |-- enable_project.py         Enables Workers for Projects
|   |-- heartbeat.py              Records Worker heartbeats
|   |-- list.py                   Lists Workers and their capacity for one Project
|   `-- response.py               Translates Worker documents to responses
`-- users/
  |-- __init__.py               Composes endpoint-specific controllers
  |-- create.py                 Creates the current User
  |-- describe_own.py           Retrieves the current User
  |-- get_own_model.py          Retrieves one model for the current User
  |-- list_own_models.py        Lists models for the current User
  |-- patch_own.py              Updates current User settings
  `-- response.py               Translates User documents to responses
```

### Catalogs

This package defines immutable, application-shipped data. It contains curated
Python definitions and typed loaders for manifest-backed Markdown resources.
It does not access SQLite or workspace state.

```text
catalogs/
|
|-- __init__.py                    Exposes the combined Persona and Skill catalog
|-- persona_skills/
|   |-- __init__.py                Defines public catalog contracts
|   |-- entries.py                 Defines immutable persona and skill entries
|   |-- errors.py                  Defines catalog loading errors
|   |-- loader.py                  Loads manifests, resources, and combined catalogs
|   |-- validation.py              Validates manifest values
|   `-- types.py                   Defines catalog metadata and value types
|-- models/
|   |-- __init__.py                Combines and validates curated entries
|   |-- items/
|   |   |-- __init__.py            Combines provider-specific model items
|   |   |-- anthropic.py           Defines Anthropic items
|   |   |-- helpers.py             Builds shared pricing and capability values
|   |   |-- nvidia.py              Defines NVIDIA items
|   |   |-- openai.py              Defines OpenAI items
|   |   `-- together.py            Defines Together items
|   |-- types.py                   Defines catalog contracts
|   `-- validation.py              Validates catalog consistency
|-- personas/
|   |-- __init__.py                Declares packaged resources
|   |-- items/                     Contains Markdown definitions
|   |-- loader.py                  Loads and validates entries
|   `-- registry.json              Declares resource metadata
|-- providers/
|   |-- __init__.py                Defines public catalog contracts
|   `-- items.py                   Defines supported provider metadata
`-- skills/
  |-- __init__.py                Declares packaged resources
  |-- items/                     Contains Markdown definitions
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
|-- activities/
|   |-- repository.py              Defines the persistence contract
|   `-- sqlite_repository.py       Persists definitions and changelog entries
|-- infrastructure/
|   |-- __init__.py                Declares database setup utilities
|   |-- local_tenant_seed.py       Creates the initial local workspace
|   |-- migration_runner.py         Discovers and applies SQLite migrations
|   `-- sqlite_database.py          Manages asynchronous SQLite connections
|-- instructions/
|   |-- __init__.py                Declares persona and skill persistence
|   |-- availability.py            Resolves scope-specific instruction availability
|   |-- mapping.py                 Maps SQLite rows and normalizes values
|   |-- mutations.py               Creates, updates, and deletes records
|   |-- repository.py              Persists resource definitions
|   |-- settings.py                Persists scope-specific enablement settings
|   `-- persona_skill_repository.py Persists persona-skill associations
|-- linked_services/
|   |-- __init__.py                Declares persistence contracts
|   `-- repository.py              Persists User-owned provider connections
|-- activity_runs/
|   |-- errors.py                  Defines checkpoint transition conflicts
|   |-- __init__.py                Declares persistence contracts
|   |-- repository.py              Defines the persistence contract
|   `-- sqlite_repository.py       Persists checkpoint records
|-- pipelines/
|   |-- __init__.py                Declares persistence contracts and adapters
|   |-- mapping.py                 Maps SQLite rows and write values
|   |-- repository.py              Defines the persistence contract
|   `-- sqlite_repository.py       Persists records and changelog entries
|-- pipeline_runs/
|   |-- __init__.py                Declares persistence contracts
|   |-- repository.py              Persists Pipeline execution state
|   `-- sqlite_repository.py       Persists Pipeline execution state
|-- providers/
|   |-- __init__.py                Declares persistence contracts
|   |-- repository.py              Defines the persistence contract
|   `-- sqlite_repository.py       Persists provider configuration
|-- shared/
|   |-- __init__.py                Declares reusable persistence adapters
|   |-- datetime.py                Maps SQLite timestamp values
|   |-- dependency_repository.py   Looks up resource dependencies
|   |-- json_mapping.py            Serializes and deserializes JSON values
|   |-- reference_repository.py    Resolves instruction and model references
|   |-- tenant_repository.py       Persists Project memberships
|   `-- validation_repository.py   Looks up normalized resource names
|-- projects/
|   |-- __init__.py                Declares persistence contracts
|   |-- repository.py              Defines the persistence contract
|   `-- sqlite_repository.py       Persists Projects
|-- worker_instances/
|   |-- __init__.py                Declares persistence contracts
|   |-- repository.py              Defines the persistence contract
|   `-- sqlite_repository.py       Persists Workers and Project enablements
|-- users/
|   |-- __init__.py                Declares persistence contracts
|   |-- repository.py              Defines the persistence contract
|   `-- sqlite_repository.py       Persists User records
```

### Models

This package defines typed internal domain state. It contains persisted
documents, immutable changelog entries, availability projections, and values
used between services and repositories. It does not define HTTP contracts.
Activity definitions currently support `approval`, `quiz`, `direct_loop`,
`refinement_loop`, and `roundtable_loop` types.

```text
models/
|
|-- activity.py                    Defines definitions and changelog entries
|-- activity_run.py                Defines Activity execution state and checkpoints
|-- changelog.py                   Defines shared immutable changelog values
|-- execution.py                   Defines private model-selection snapshots
|-- linked_service.py              Defines User-owned provider connections
|-- pipeline.py                    Defines definitions, steps, and history
|-- pipeline_run.py                Defines frozen Pipeline execution state and events
|-- reference.py                   Defines dependency and reference values
|-- worker_instance.py             Defines Worker identities and Project enablements
|-- tenant.py                      Defines workspace and membership state
|-- user.py                        Defines persisted user identities
|-- workspace.py                   Defines Workspace documents
`-- worker.py                      Defines Worker registration and Harness state
```

## Components

- [Execution lifecycle](components/execution-lifecycle.md) describes persisted
  runs, checkpoints,
  prompts, review, finalisation, artefacts, and metrics.
- [Persona and Skill catalog](components/persona-skill-catalog.md) describes
  builtin Persona and Skill ownership, synchronization, and maintenance.
