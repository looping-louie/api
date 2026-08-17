# API

Looping Louie API exposes a versioned API for managing the resources used by
the execution runtime and for persisting activity-run checkpoints.

The endpoint reference is organized by top-level router:

- [Endpoint overview](endpoints/overview.md) covers authentication, workspace
  selection, pagination, mutation conventions, and error responses.
- [Catalog](endpoints/catalog.md) exposes static provider and model definitions.
- [Providers](endpoints/providers.md) manages model-provider configuration.
- [Models](endpoints/models.md) exposes the curated model catalog.
- [Personas](endpoints/personas.md) manages persona instructions.
- [Skills](endpoints/skills.md) manages skill instructions.
- [Activities](endpoints/activities.md) manages reusable concrete Activity
  definitions, including Activity runs.
- [Pipelines](endpoints/pipelines.md) manages ordered Activity definitions and
  persists each supplied step as an independent Activity record.

The API owns planning, generation, and reviewer decisions. The CLI owns local
repository execution, including filesystem, Git, and workspace lifecycle
operations.
