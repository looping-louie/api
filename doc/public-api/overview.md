# Public API Overview

Looping Louie API exposes a versioned API for managing the resources used by
the execution runtime and for persisting Activity-run checkpoints.

The API owns planning, generation, reviewer decisions, Harness selection, and
durable execution state. The runtime owns local repository execution, including
filesystem, Git, Project lifecycle operations, and Worker-local Harness
configuration.

## Endpoint reference

- [Catalog](catalog.md) exposes static provider, model, built-in Persona, and
  built-in Skill definitions.
- [Users](users.md) registers and retrieves the current API user.
- [Linked Services](linked-services.md) manages User-owned provider
  connections.
- [Projects](projects.md) manages User-owned execution-placement Projects.
- [Personas](personas.md) manages persona instructions.
- [Skills](skills.md) manages skill instructions.
- [Activities](activities.md) manages User-owned reusable concrete Activity
  definitions and their Project-placed Activity runs.
- [Pipelines](pipelines.md) manages User-owned ordered Activity definitions and
  persists each supplied step as an independent User-owned Activity record.
- [Workers](workers.md) registers User-owned Workers, controls their Project
  enablements, and records their heartbeats.

## Versioned API conventions

All catalog, linked-service, project, model, persona, skill,
activity, and pipeline routes use the `/api/v1` prefix.

These routes require a user identity. Until authentication is implemented,
clients provide it through `X-User-ID`. In local development,
`LOUIE_DEV_AUTH=true` injects `LOUIE_DEV_USER_ID` when the request does not
already have an identity. A request may select one of the User's Projects with
the optional `X-Project-ID` header when it targets legacy execution placement,
PipelineRun, or ActivityRun. Worker enablement routes identify the
Project explicitly in their path or request body. Project management routes
instead include the Project identifier in their URL. User model routes are
user-scoped and ignore the header.
If the User has access to more than one Project and the header is omitted, the
API returns `409 project_selection_required`.

Persona, Skill, Linked Service, standalone Activity, and Pipeline definition
routes are user-scoped: their custom definitions, enablement settings, provider
connections, Activity definitions, and Pipeline definitions belong to
`X-User-ID`, and they ignore `X-Project-ID`.

Persona, Skill, Activity, Pipeline, User Model, and catalog Model lists
return an object with `items` and `total`. Catalog provider, built-in Persona,
and built-in Skill lists, plus linked-service lists, return JSON arrays. The
optional `search` query parameter accepted by resource lists is case-insensitive
and must contain between 1 and 200 characters. Activity and activity-changelog
lists accept a non-negative `offset` and always return at most ten items.
Pipeline lists also use fixed ten-item pages, support `status` and `search`, and
exclude archived pipelines unless `status=archived` is requested.

Create operations return `201 Created`. Persona and skill content updates use
optimistic concurrency and require the current positive integer
`expected_version`; activity updates do not.

## Shared Field Formats

The following format applies to Activity and Pipeline `name` fields, including
inline Activity definitions. Persona names retain the stricter format described
in the Persona endpoint reference.

| Field | JSON type | Required | Restrictions |
| ----- | --------- | -------- | ------------ |
| `name` | String | Yes on create; no on update | Contains 1 to 140 characters. Starts with a Unicode letter, number, or `_`. May contain spaces but not line breaks, tabs, `.`, `+`, `?`, `/`, `<`, `>`, `*`, `%`, `&`, or `:`. |

Successful deletes return:

```json
{
  "deleted": true
}
```

Domain errors use this envelope:

```json
{
  "error": {
    "code": "version_conflict",
    "message": "The resource has changed.",
    "details": {
      "expected_version": 1,
      "current_version": 2
    }
  }
}
```
