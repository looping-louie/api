# API

Looping Louie API exposes a versioned API for managing the resources used by
the execution runtime and for persisting activity-run checkpoints.

The endpoint reference is organized by top-level router:

- [Endpoint overview](endpoints/overview.md) covers authentication, workspace
  selection, pagination, mutation conventions, and error responses.
- [Catalog](endpoints/catalog.md) exposes static provider, model, built-in
  Persona, and built-in Skill definitions.
- [Users](endpoints/users.md) registers and retrieves the current API user.
- [Linked Services](endpoints/linked-services.md) manages User-owned
  provider connections.
- [Workspaces](endpoints/workspaces.md) manages User-owned Workspaces,
  their execution defaults, and model availability.
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

Workspace, Pipeline, and Activity definitions persist nullable `model_id`
and `harness` overrides. Loop agents can persist a nullable `model_id` in
their typed configuration. PipelineRun creation resolves model IDs at agent,
Activity, Pipeline, then Workspace scope. For `louie`, run creation requires
an effective model ID, selects the first deterministically ordered compatible,
enabled, configured Linked Service, and freezes a private `model_target`
snapshot. `codex_cli` does not select API Linked Services or require API
provider credentials. Harnesses resolve at Activity, Pipeline, Workspace, then
User scope. A missing Louie agent model fails run creation; Personas contribute
instructions only. When no Harness candidate exists, the frozen Harness is the
`louie` v1 compatibility default.

User settings also gate logical model availability. Unconfigured models inherit
`settings.default_model_availability`, which defaults to `enabled`;
`settings.configured_models` overrides that status per model ID. A disabled
model is unavailable in Workspace catalog responses and cannot be resolved by
the `louie` Harness, even when a compatible Linked Service is ready.

Workers advertise their available Harness capabilities during registration. A
PipelineRun claim requires an active Worker heartbeat and an exact match for
the frozen Pipeline Harness selection.

Workspace defaults use explicit nullable values: an absent `model_id` or
`harness` means the workspace inherits that value from a higher-level or
system-level source. PipelineRun creation consumes Workspace candidates only
after all narrower Pipeline and Activity candidates are considered, and before
the User's `settings.default_harness` value.
