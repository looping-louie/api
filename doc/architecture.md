# Looping Louie Architecture

Looping Louie API is the decision engine for iterative LLM software
development. It persists pipeline and activity state while the runtime executes
repository changes on a worker.

The runtime is independent from any programming language, framework, or LLM
provider.

## Worker provisioning

The API provisions each Project worker identity. The runtime stores the
assigned ID in its Project configuration and refreshes its heartbeat before
polling. PipelineRun claims require an active worker heartbeat, while the
existing PipelineRun lease continues to authorize only one claimed run.
Heartbeat liveness never renews or revokes a lease.

## Ownership boundaries

The API owns User and Project resource management, including User-owned
Activity and Pipeline definitions, Project membership, durable Pipeline and
Activity-run state, prompt generation, model decisions, and checkpoint
transitions. Pipeline and Activity definitions are independent of execution
placement; Pipeline and Activity runs remain Project-placed. The runtime owns
Project lifecycle, repository inspection, filesystem changes, Git
operations, and activity execution after it claims a queued pipeline run.

## Execution defaults

User settings persist optional `default_model_id` and `default_harness`
overrides. A missing value explicitly means no User-level default.

User settings also persist model availability policy. Unconfigured logical
models inherit `default_model_availability`, which defaults to `enabled`, and
`configured_models` overrides the status per model ID. This policy gates both
current-User catalog availability and `louie` User-owned Linked Service
selection; provider readiness remains required for an enabled model.

The hierarchy persists candidates at User, Pipeline, Activity, and loop-agent
scopes. Pipeline and Activity store first-class nullable
`model_id` and `harness` fields; agents store nullable `model_id` in their
typed loop configuration.
It is intentionally separate from Personas, which are reusable instructions
rather than model-routing or provider-connection resources. PipelineRun
creation resolves and freezes effective values: agent, Activity, Pipeline, then
User for model IDs; and Activity, Pipeline, then User for Harnesses.
For `louie`, creation requires an effective model ID and selects the first
deterministically ordered compatible, enabled, configured User-owned Linked
Service before freezing its identity and owner in a private `model_target`
snapshot. `codex_cli` does not select API Linked Services or require API
provider credentials. For each Codex Activity, creation freezes the effective
generator model as `requested_model`, resolves the generator Persona and its
ordered Skills from the User-owned library, and freezes their versioned content
in the Activity snapshot delivered through `run_harness`. A Codex Activity
without an effective model ID fails run creation; Personas are instruction-only
resources. An unset effective Harness becomes the `louie` v1
compatibility default after considering the User default. Projects continue to
select execution placement only.

## Harnesses

A Harness is the local execution mechanism for runtime-executable Activities.
It is distinct from an Activity agent: an agent is a generator, reviewer, or
aggregator role backed by a Persona and model selection; a Harness carries out
the Activity in a worker's configured checkout and reports normalized results.

The API-directed repository executor is the `louie` Harness. It
collects repository context, applies API-approved file operations, gathers
review input, and commits only when the API authorizes the handoff. `louie` v1
is the compatibility default for existing Pipelines.

A Pipeline may select one Harness for its runtime-executable Activities. Human
Activities (`approval` and `quiz`) remain intrinsically human-executed and do
not use the selected Harness. PipelineRun creation freezes the effective
Harness for each Activity, preferring its own override before Pipeline and
User candidates, then using the `louie` v1 compatibility
default. A Pipeline edit must not change the Harness used by an existing run.

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
diagnostics, requested model, actual model, and optional opaque session
reference through `run_harness`. The payload includes the immutable effective
model and Persona and Skill snapshot resolved at run creation, so the runtime
does not query mutable resources during execution. The API rejects a successful
result whose requested model differs from the snapshot. For commit-enabled
runs, Codex also proposes a non-empty commit
message in its normalized Harness result. The API persists that proposal and
returns it only when the Activity reaches `commit_if_allowed`, preserving the
same commit-authorization boundary used by the `louie` Harness.

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
|-- projects/
|   |-- __init__.py                Defines the package's public imports
|   `-- service.py                 Manages User-owned execution-placement Projects
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
|-- workers/
|   |-- __init__.py               Composes endpoint-specific controllers
|   |-- create.py                 Creates Workers
|   |-- heartbeat.py              Records Worker heartbeats
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
|-- users/
|   |-- __init__.py                Declares persistence contracts
|   |-- repository.py              Defines the persistence contract
|   `-- sqlite_repository.py       Persists User records
`-- workers/
  |-- __init__.py                Declares persistence contracts
  |-- repository.py              Defines the persistence contract
  `-- sqlite_repository.py       Persists Worker records
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
|-- tenant.py                      Defines workspace and membership state
|-- user.py                        Defines persisted user identities
|-- workspace.py                   Defines Workspace documents
`-- worker.py                      Defines Worker registration and Harness state
```

## Components

- [Execution](components/execution.md) describes persisted runs, checkpoints,
  prompts, review, finalisation, artefacts, and metrics.
- [Activities](components/activities.md) defines Activity categories, loop
  roles, and supported Activity-run behavior.
- [Persona and Skill catalog](components/persona-skill-catalog.md) describes
  builtin Persona and Skill ownership, synchronization, and maintenance.
- [Providers](components/providers.md) records the static provider and model
  catalog boundary. Linked Services persist independent User-owned provider
  connections and derive their available deployment models from that catalog.
  Legacy provider credentials and Persona model associations are retired.
- [Philosophy](components/philosophy.md) contains the project principles and
  long-term direction.
- [Current limitations](components/limitations.md) records known MVP
  boundaries.
