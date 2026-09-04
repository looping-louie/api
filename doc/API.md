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
  discovery and event ledgers, and human Activity-run decisions.
- [Workers](endpoints/workers.md) provisions runtime identities and records
  liveness heartbeats required for PipelineRun claims.

The API owns planning, generation, reviewer decisions, Harness selection, and
durable execution state. The runtime owns local repository execution, including
filesystem, Git, workspace lifecycle operations, and Worker-local Harness
configuration. The CLI submits and manages API resources.
