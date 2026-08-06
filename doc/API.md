# API

Looping Louie API exposes a versioned API for managing the resources used by
the execution runtime and for persisting loop-run checkpoints.

The endpoint reference is organized by top-level router:

- [Endpoint overview](endpoints/overview.md) covers authentication, workspace
  selection, pagination, mutation conventions, and error responses.
- [Providers](endpoints/providers.md) manages model-provider configuration.
- [Models](endpoints/models.md) exposes the curated model catalog.
- [Personas](endpoints/personas.md) manages persona instructions.
- [Skills](endpoints/skills.md) manages skill instructions.
- [Loops](endpoints/loops.md) manages stored multi-agent loop definitions and
  nested loop runs.
- [Pipelines](endpoints/pipelines.md) manages ordered loop and human-gate
  definitions.

The API owns planning, generation, and reviewer decisions. The CLI owns local
repository execution, including filesystem, Git, and workspace lifecycle
operations.
