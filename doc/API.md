# API

Looping Louie API exposes a versioned API for managing the resources used by
the execution runtime and for persisting activity-run checkpoints.

The endpoint reference is organized by top-level router:

- [Endpoint overview](endpoints/overview.md) covers authentication, Project
  selection, pagination, mutation conventions, and error responses.
- [Catalog](endpoints/catalog.md) exposes static provider, model, built-in
  Persona, and built-in Skill definitions.
- [Users](endpoints/users.md) manages the current API user, execution settings,
  and model availability.
- [Linked Services](endpoints/linked-services.md) manages User-owned
  provider connections.
- [Projects](endpoints/projects.md) manages User-owned execution-placement
  Projects.
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

User, Pipeline, and Activity definitions persist nullable `model_id`
and `harness` overrides. Loop agents can persist a nullable `model_id` in
their typed configuration. PipelineRun creation resolves model IDs at agent,
Activity, Pipeline, then User scope. For `louie`, run creation requires
an effective model ID, selects the first deterministically ordered compatible,
enabled, configured User-owned Linked Service, and freezes its identity and
owner in a private `model_target` snapshot. `codex_cli` does not select API
Linked Services or require API provider credentials. Instead, PipelineRun
creation freezes the effective generator model as `requested_model`, resolves
the selected generator Persona and its ordered Skills from the User-owned
instruction library, and freezes their IDs, versions, metadata, and content in
the Activity snapshot. The `run_harness` payload exposes that same immutable
model and instruction snapshot to the runtime. Harnesses resolve at Activity,
Pipeline, then User scope. A missing effective model fails run creation;
Personas contribute instructions only. When no Harness candidate exists, the
frozen Harness is the `louie` v1 compatibility default.

A successful `codex_cli` result includes a proposed `commit_message` whenever
the frozen commit mode allows commits. The API validates and persists that
message as a runtime artifact, then exposes it only through the later
`commit_if_allowed` checkpoint. Codex does not authorize or perform the commit.
The normalized result remains available in the ActivityRun `payload` on both
success and failure. Every observation carries `schema_version` and the frozen
Harness identity before the common timing, model, usage, process, Git, response,
and error fields. Harness-specific fields extend that common envelope; the
`codex_cli` v1 variant includes reasoning effort, session reference, and
materialized Skill IDs and versions. The requested model and reported Harness
must match the immutable Activity snapshot. A later authorized commit updates
the final commit SHA without discarding the Harness observation.

The PipelineRun event ledger records `pipeline_run_claimed`,
`pipeline_step_started`, terminal step events, and `harness_turn_completed` or
`harness_turn_failed` in addition to `pipeline_run_created`. Harness turn events
contain the same normalized observation exposed by the child ActivityRun and
identify the implementation through `payload.harness.kind`.

User settings also gate logical model availability. Unconfigured models inherit
`settings.default_model_availability`, which defaults to `enabled`;
`settings.configured_models` overrides that status per model ID. A disabled
model cannot be frozen into a new run. Current-User catalog responses expose
this policy as top-level `enabled`, independently from top-level `available`,
which additionally requires a usable Linked Service and therefore describes
`louie` execution readiness. `codex_cli` uses `enabled` because its
authentication remains local to the worker.

Workers advertise their current Harness capabilities during registration and
may replace them on every heartbeat. A PipelineRun claim requires an active
Worker heartbeat and an exact match for the next claimable Activity's frozen
Harness selection.
A valid run remains queued when no compatible worker is healthy and becomes
claimable without a user retry after a later heartbeat advertises that Harness.
The run-readiness endpoint exposes Project-scoped aggregate counts and the
required Harness for operator diagnostics without exposing Worker identities or
local configuration.
Registration and heartbeat requests carry both the acting `X-User-ID` and
selected `X-Project-ID`.

User settings use explicit nullable values: an absent `default_model_id` or
`default_harness` leaves the value unset after narrower Activity and Pipeline
candidates are considered. Workspaces select where a run executes; they do not
contribute model or Harness policy.
