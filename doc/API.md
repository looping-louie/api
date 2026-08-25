# API

Looping Louie API exposes a versioned API for managing the resources used by
the execution runtime and for persisting activity-run checkpoints.

The endpoint reference is organized by top-level router:

- [Endpoint overview](endpoints/overview.md) covers authentication, workspace
  selection, pagination, mutation conventions, and error responses.
- [Catalog](endpoints/catalog.md) exposes static provider and model definitions.
- [Linked Services](endpoints/linked-services.md) manages workspace-owned
  provider connections.
- [Workspaces](endpoints/workspaces.md) manages workspace-owned execution
  defaults.
- [Models](endpoints/models.md) exposes the curated model catalog.
- [Personas](endpoints/personas.md) manages persona instructions.
- [Skills](endpoints/skills.md) manages skill instructions.
- [Activities](endpoints/activities.md) manages reusable concrete Activity
  definitions, including Activity runs.
- [Pipelines](endpoints/pipelines.md) manages ordered Activity definitions and
  persists each supplied step as an independent Activity record, Pipeline-run
  event ledgers, and human Activity-run decisions.
- [Workers](endpoints/workers.md) provisions runtime identities and records
  liveness heartbeats required for PipelineRun claims.

The API owns planning, generation, reviewer decisions, Harness selection, and
durable execution state. The runtime owns local repository execution, including
filesystem, Git, workspace lifecycle operations, and Worker-local Harness
configuration. The CLI submits and manages API resources.

Workspace, Pipeline, and Activity definitions persist nullable `model_target`
and `harness` overrides. Loop agents can persist a nullable `model_target` in
their typed configuration while retaining legacy `model_id`. Every non-null
model target is validated against an enabled, configured linked service and an
active model deployment in the selected workspace. These are configuration
scopes only: PipelineRun does not yet resolve them by hierarchy. It continues
to snapshot an explicit Pipeline Harness, or the legacy `louie` v1 compatibility
default when the Pipeline Harness override is unset.

Workers advertise their available Harness capabilities during registration. A
PipelineRun claim requires an active Worker heartbeat and an exact match for
the frozen Pipeline Harness selection.

Workspace defaults use explicit nullable values: an absent `model_target` or
`harness` means the workspace inherits that value from a higher-level or
system-level source. Workspace default candidates are persisted now; Pipeline
and Activity resolution will consume them when the execution-default hierarchy
is completed.
