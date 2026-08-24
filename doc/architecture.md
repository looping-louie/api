# Looping Louie Architecture

Looping Louie API is the decision engine for iterative LLM software
development. It persists pipeline and activity state while the runtime executes
repository changes on a worker.

The runtime is independent from any programming language, framework, or LLM
provider.

## Worker provisioning

The API provisions each workspace worker identity. The runtime stores the
assigned ID in its workspace configuration and refreshes its heartbeat before
polling. PipelineRun claims require an active worker heartbeat, while the
existing PipelineRun lease continues to authorize only one claimed run.
Heartbeat liveness never renews or revokes a lease.

## Ownership boundaries

The API owns resource management, durable pipeline and activity-run state,
prompt generation, model decisions, and checkpoint transitions. The runtime
owns workspace lifecycle, repository inspection, filesystem changes, Git
operations, and activity execution after it claims a queued pipeline run.

## Harnesses

A Harness is the local execution mechanism for runtime-executable Activities.
It is distinct from an Activity agent: an agent is a generator, reviewer, or
aggregator role backed by a Persona and model selection; a Harness carries out
the Activity in a worker's configured checkout and reports normalized results.

The API-directed repository executor is the `louie` Harness. It
collects repository context, applies API-approved file operations, gathers
review input, and commits only when the API authorizes the handoff. `louie` v1
is the compatibility default for existing Pipelines.

A Pipeline selects one Harness for its runtime-executable Activities. Human
Activities (`approval` and `quiz`) remain intrinsically human-executed and do
not use the selected Harness. The Pipeline-run snapshot freezes the selected
Harness and its configuration; each child Activity-run receives that frozen
selection. A Pipeline edit must not change the Harness used by an existing run.

Harness definitions use a stable kind, a version, and a kind-specific `config`
object. The implemented `louie` v1 configuration must be empty. The API stores
only policy that it can validate and audit. Worker-local configuration,
including checkout paths, executable locations, credentials, and secrets,
remains outside Pipeline definitions.

```json
{
  "harness": {
    "kind": "louie",
    "version": "v1",
    "config": {}
  }
}
```

Harness kinds retain the same configuration shape. `codex_cli` v1 currently
uses an empty configuration. Its executable, sandbox policy, timeout,
credentials, and other local settings remain Worker-owned:

```json
{
  "harness": {
    "kind": "codex_cli",
    "version": "v1",
    "config": {}
  }
}
```

`codex_cli` supports a single `direct_loop` turn. It does not replace
API-directed scheduling, reviewer decisions, lease validation, or commit
authorization. Workers advertise Harness capabilities during registration, and
the API requires an exact capability match before a PipelineRun claim. The
runtime reports the turn's final response, checkout diff, changed files, usage,
diagnostics, and optional opaque session reference through `run_harness`.

The API and runtime coordinate through the activity-run checkpoint protocol
documented in [Execution](components/execution.md). The API never mutates the
target repository directly, and the runtime does not make model or reviewer
decisions. A claimed runtime worker must present its active lease token before
it checkpoints an Activity child or advances Pipeline scheduling; the API
rejects stale workers before either durable mutation.

When API-owned generation detects a classified model catalog failure while
processing a valid checkpoint, the API records a terminal failed Activity with
a structured failure reason. It does not leave the claimed Pipeline child
reclaimable after returning the error to the runtime.

Each Pipeline run freezes its `commit_mode` authorization policy. A `forbid`
run completes after approved operations without emitting a commit checkpoint;
the runtime's local Git policy may further deny an allowed commit but cannot
grant one forbidden by the persisted run policy.

Pipeline runs preserve an append-only event ledger. A ready `approval` or
`quiz` Activity creates a normal child Activity run with a human executor and
transitions the Pipeline to `waiting` without assigning a worker lease. Users
submit its decision through the Activity-run continuation API. A rejected
human Activity run resets frozen predecessor steps for corrective execution;
the scheduler creates a new human child after those steps complete again.

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
|-- instructions/
|   |-- __init__.py                Defines the package's public imports
|   |-- synchronization/
|   |   |-- __init__.py            Defines the package's public imports
|   |   |-- serialization.py       Serializes catalog entries for persistence
|   |   `-- synchronizer.py        Materializes builtins in SQLite, applies
|   |                              version and checksum policy, deprecates
|   |                              removed entries, and synchronizes
|   |                              persona-skill associations
|   |-- service.py                 Coordinates resource operations
|   |-- types.py                   Defines contracts and domain errors
|   `-- validation.py              Normalizes and validates input
|-- linked_services/
|   |-- __init__.py                Defines the package's public imports
|   `-- service.py                 Manages workspace-owned provider connections
|-- model_execution/
|   |-- __init__.py                Defines the package's public imports
|   `-- service.py                 Invokes provider-neutral endpoints through
|                                  an explicit Linked Service or legacy fallback
|-- models/
|   |-- __init__.py                Defines the package's public imports
|   |-- availability.py            Calculates workspace availability
|   `-- catalog.py                 Queries the curated model catalog
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
|-- pipeline_runs/
|   |-- __init__.py                Defines the package's public imports
|   |-- etag.py                    Creates concurrency entity tags
|   |-- service.py                 Creates, reads, and advances Pipeline runs
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
|   |-- reference_resolver.py      Resolves references between workspace resources
|   |-- settings.py                Loads environment-backed application settings
|   |-- tenant.py                  Resolves workspace tenancy and memberships
|   `-- validation.py              Provides reusable domain validations
|-- skills/
|   |-- __init__.py                Defines the package's public imports
|   |-- metadata_validator.py      Validates structured metadata
|   `-- service.py                 Manages workspace resources
`-- workers/
    |-- __init__.py                Defines the package's public imports
    `-- service.py                 Manages worker registration and liveness
```

### Controllers

This package translates HTTP schemas to application service calls and
application results to HTTP schemas. Resource packages compose endpoint-specific
controllers for router compatibility; routers retain route declarations,
dependency injection, and request extraction.

```text
controllers/
|
|-- catalog/
|   |-- __init__.py               Defines public controller imports
|   `-- controller.py             Returns static catalog resources
|-- activity/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- create.py                 Creates definitions
|   |-- delete.py                 Deletes definitions
|   |-- describe.py               Describes one definition
|   |-- list.py                   Lists definitions
|   |-- list_changelog.py         Lists changelog entries
|   |-- patch.py                  Applies supplied changes
|   `-- utils.py                  Translates patch schemas to service changes
|-- activity_run.py               Coordinates Activity-run HTTP operations
|-- activity_runs/
|   `-- utils.py                  Translates checkpoint results to responses
|-- linked_services/
|   `-- __init__.py               Composes Linked Service controllers
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
|   |-- availability.py            Persists workspace availability settings
|   |-- mapping.py                 Maps SQLite rows and normalizes values
|   |-- mutations.py               Creates, updates, and deletes records
|   |-- persona_linked_service_selection_repository.py Persists persona service selections
|   |-- repository.py              Persists resource definitions
|   |-- settings.py                Persists workspace enablement settings
|   `-- persona_skill_repository.py Persists persona-skill associations
|-- linked_services/
|   `-- repository.py              Persists workspace provider connections
|-- activity_runs/
|   |-- errors.py                  Defines checkpoint transition conflicts
|   |-- repository.py              Defines the persistence contract
|   `-- sqlite_repository.py       Persists checkpoint records
|-- pipelines/
|   |-- __init__.py                Declares persistence contracts and adapters
|   |-- mapping.py                 Maps SQLite rows and write values
|   |-- repository.py              Defines the persistence contract
|   `-- sqlite_repository.py       Persists records and changelog entries
|-- pipeline_runs/
|   `-- repository.py              Persists Pipeline execution state
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
Activity definitions currently support `approval`, `quiz`, `direct_loop`,
`refinement_loop`, and `roundtable_loop` types.

```text
models/
|
|-- activity.py                    Defines definitions and changelog entries
|-- activity_run.py                Defines Activity execution state and checkpoints
|-- changelog.py                   Defines shared immutable changelog values
|-- instruction.py                 Defines persisted and available resource data
|-- linked_service.py              Defines workspace-owned provider connections
|-- model.py                       Defines catalog and availability projections
|-- persona.py                     Defines resource documents with skill links
|-- pipeline.py                    Defines definitions, steps, and history
|-- reference.py                   Defines dependency and reference values
`-- tenant.py                      Defines workspace and membership state
```

## Components

- [Execution](components/execution.md) describes persisted runs, checkpoints,
  prompts, review, finalisation, artefacts, and metrics.
- [Activities](components/activities.md) defines Activity categories, loop
  roles, and supported Activity-run behavior.
- [Instruction catalog](components/instruction-catalog.md) describes builtin
  instruction ownership, synchronization, and maintenance.
- [Providers](components/providers.md) records the static provider and model
  catalog boundary. Linked Services persist independent workspace-owned provider
  connections and derive their available deployment models from that catalog.
  Persona linked-service selections are workspace-scoped and require an enabled,
  configured service with an active compatible deployment. During execution, a
  selection routes its model request through that exact service. Legacy provider
  credentials and Persona model associations are retired.
- [Philosophy](components/philosophy.md) contains the project principles and
  long-term direction.
- [Current limitations](components/limitations.md) records known MVP
  boundaries.
